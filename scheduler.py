import random
import copy

def parse_dataset(text):
    """
    Parses the scheduling input text.
    Expected sections:
    [Days]
    Monday, Tuesday, ...
    
    [TimeSlots]
    09:00-10:00, ...
    
    [Rooms]
    Room 101, ...
    
    [Faculty]
    Dr. Smith: Math, Physics
    Dr. Jones: Chemistry | Unavailable: Monday 09:00-10:00
    
    [Requirements]
    Grade 10: Math, 3, Dr. Smith
    """
    lines = [line.strip() for line in text.split('\n')]
    current_section = None
    
    days = []
    slots = []
    rooms = []
    faculty = {}
    requirements = []
    
    for line in lines:
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1].strip().lower()
            continue
        
        if current_section == 'days':
            parts = [p.strip() for p in line.split(',') if p.strip()]
            days.extend(parts)
        elif current_section == 'timeslots':
            parts = [p.strip() for p in line.split(',') if p.strip()]
            slots.extend(parts)
        elif current_section == 'rooms':
            parts = [p.strip() for p in line.split(',') if p.strip()]
            rooms.extend(parts)
        elif current_section == 'faculty':
            if ':' not in line:
                continue
            name_part, rest = line.split(':', 1)
            name = name_part.strip()
            
            subjects_part = rest
            unavailable_slots = set()
            if '|' in rest:
                subjects_part, unavail_part = rest.split('|', 1)
                if 'unavailable:' in unavail_part.lower():
                    _, unavail_list = unavail_part.lower().split('unavailable:', 1)
                    unavail_tokens = [t.strip() for t in unavail_list.split(',') if t.strip()]
                    for tok in unavail_tokens:
                        tok_parts = tok.split()
                        if len(tok_parts) >= 2:
                            uday = tok_parts[0].strip().lower()
                            uslot = " ".join(tok_parts[1:]).strip().lower()
                            unavailable_slots.add((uday, uslot))
            
            subjects = [s.strip() for s in subjects_part.split(',') if s.strip()]
            faculty[name] = {
                'subjects': subjects,
                'unavailable': unavailable_slots
            }
        elif current_section == 'requirements':
            if ':' not in line:
                continue
            group_part, rest = line.split(':', 1)
            group = group_part.strip()
            
            req_parts = [r.strip() for r in rest.split(',') if r.strip()]
            if len(req_parts) >= 3:
                subject = req_parts[0]
                try:
                    hours = int(req_parts[1])
                except ValueError:
                    hours = 1
                preferred_faculty = req_parts[2]
                requirements.append({
                    'group': group,
                    'subject': subject,
                    'hours': hours,
                    'preferred_faculty': preferred_faculty
                })
                
    # Normalize days and slots to lists of unique, stripped strings
    days = [d.strip() for d in days if d.strip()]
    slots = [s.strip() for s in slots if s.strip()]
    rooms = [r.strip() for r in rooms if r.strip()]
    
    return {
        'days': days,
        'slots': slots,
        'rooms': rooms,
        'faculty': faculty,
        'requirements': requirements
    }

class Scheduler:
    def __init__(self, dataset, pop_size=50, mutation_rate=0.2, crossover_rate=0.8, elitism_size=3):
        self.days = dataset['days']
        self.slots = dataset['slots']
        self.rooms = dataset['rooms']
        self.faculty = dataset['faculty']
        self.requirements = dataset['requirements']
        
        self.pop_size = pop_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_size = elitism_size
        
        # Build the session list (the genes to schedule)
        self.sessions = []
        session_id = 0
        for req in self.requirements:
            for _ in range(req['hours']):
                self.sessions.append({
                    'id': session_id,
                    'group': req['group'],
                    'subject': req['subject'],
                    'faculty': req['preferred_faculty']
                })
                session_id += 1
                
        self.population = []
        
    def generate_random_gene(self):
        return {
            'day': random.choice(self.days),
            'slot': random.choice(self.slots),
            'room': random.choice(self.rooms)
        }
        
    def initialize_population(self):
        self.population = []
        for _ in range(self.pop_size):
            # A chromosome is a list of genes corresponding to self.sessions
            chromosome = [self.generate_random_gene() for _ in range(len(self.sessions))]
            self.population.append(chromosome)
            
    def calculate_fitness(self, chromosome):
        """
        Calculates conflicts and returns a fitness score.
        Returns:
            fitness: float in [0, 1]
            hard_conflicts_count: int
            soft_conflicts_count: int
            details: dict containing lists of specific conflict descriptions
        """
        hard_conflicts = 0
        soft_conflicts = 0
        
        # We need tracking lists of what is scheduled when
        # Key: (day, slot, resource) -> values
        faculty_schedule = {}
        room_schedule = {}
        group_schedule = {}
        
        # Detailed conflict reports
        overlap_faculty = []
        overlap_room = []
        overlap_group = []
        unavailability_violations = []
        soft_gap_violations = []
        soft_dist_violations = []
        
        # Store conflicted session IDs
        conflicted_session_ids = set()
        
        # Group and faculty class assignments per day (for soft constraints)
        group_daily_classes = {} # (group, day) -> list of slots
        group_daily_subjects = {} # (group, day, subject) -> count
        faculty_daily_classes = {} # (faculty, day) -> list of slots
        
        for idx, gene in enumerate(chromosome):
            session = self.sessions[idx]
            day = gene['day']
            slot = gene['slot']
            room = gene['room']
            faculty_member = session['faculty']
            group = session['group']
            subject = session['subject']
            
            # 1. Faculty overlapping check preparation
            if faculty_member:
                fac_key = (day, slot, faculty_member)
                faculty_schedule.setdefault(fac_key, []).append(session)
                
                # Check faculty availability
                fac_info = self.faculty.get(faculty_member)
                if fac_info and 'unavailable' in fac_info:
                    if (day.lower(), slot.lower()) in fac_info['unavailable']:
                        hard_conflicts += 1
                        unavailability_violations.append(
                            f"{faculty_member} is scheduled at {day} {slot} but is marked Unavailable."
                        )
                        conflicted_session_ids.add(session['id'])
                
                # Soft constraint prep
                fac_day_key = (faculty_member, day)
                faculty_daily_classes.setdefault(fac_day_key, []).append(slot)
            
            # 2. Room overlapping check preparation
            room_key = (day, slot, room)
            room_schedule.setdefault(room_key, []).append(session)
            
            # 3. Student Group overlapping check preparation
            group_key = (day, slot, group)
            group_schedule.setdefault(group_key, []).append(session)
            
            # Soft constraint prep (Group)
            grp_day_key = (group, day)
            group_daily_classes.setdefault(grp_day_key, []).append(slot)
            
            # Subject distribution check prep
            subj_day_key = (group, day, subject)
            group_daily_subjects[subj_day_key] = group_daily_subjects.get(subj_day_key, 0) + 1
            
        # Count overlapping hard conflicts
        for (day, slot, fac), sessions in faculty_schedule.items():
            if len(sessions) > 1:
                # E.g., if faculty member has 2 classes in the same slot
                hard_conflicts += (len(sessions) - 1)
                overlap_faculty.append(
                    f"Faculty {fac} is double-booked at {day} {slot} ({len(sessions)} classes)."
                )
                for s in sessions:
                    conflicted_session_ids.add(s['id'])
                
        for (day, slot, rm), sessions in room_schedule.items():
            if len(sessions) > 1:
                hard_conflicts += (len(sessions) - 1)
                overlap_room.append(
                    f"Room {rm} is double-booked at {day} {slot} ({len(sessions)} classes)."
                )
                for s in sessions:
                    conflicted_session_ids.add(s['id'])
                
        for (day, slot, grp), sessions in group_schedule.items():
            if len(sessions) > 1:
                hard_conflicts += (len(sessions) - 1)
                overlap_group.append(
                    f"Student group {grp} has multiple classes at {day} {slot} ({len(sessions)} classes)."
                )
                for s in sessions:
                    conflicted_session_ids.add(s['id'])
                
        # 4. Soft constraint: Daily subject limit (no more than 2 sessions of same subject per day)
        for subj_day_key, count in group_daily_subjects.items():
            if count > 2:
                excess = count - 2
                soft_conflicts += excess
                soft_dist_violations.append(
                    f"{subj_day_key[0]} has {count} classes of {subj_day_key[2]} on {subj_day_key[1]} (limit 2)."
                )
                
        # Helper to compute gaps in a list of slots
        # slots list holds string values. We map them to indices in self.slots
        slot_index_map = {slot: idx for idx, slot in enumerate(self.slots)}
        
        # 5. Soft constraint: Gaps in student schedules
        for grp_day_key, day_slots in group_daily_classes.items():
            if len(day_slots) > 1:
                indices = sorted([slot_index_map[s] for s in day_slots if s in slot_index_map])
                if len(indices) > 1:
                    # check if there are gaps (e.g. indices are [0, 2], gap is 1)
                    min_idx = min(indices)
                    max_idx = max(indices)
                    # total possible slots between min and max
                    total_slots = max_idx - min_idx + 1
                    gaps = total_slots - len(indices)
                    if gaps > 0:
                        soft_conflicts += gaps
                        soft_gap_violations.append(
                            f"Group {grp_day_key[0]} has {gaps} free period gaps on {grp_day_key[1]}."
                        )
                        
        # 6. Soft constraint: Gaps in faculty schedules
        for fac_day_key, day_slots in faculty_daily_classes.items():
            if len(day_slots) > 1:
                indices = sorted([slot_index_map[s] for s in day_slots if s in slot_index_map])
                if len(indices) > 1:
                    min_idx = min(indices)
                    max_idx = max(indices)
                    total_slots = max_idx - min_idx + 1
                    gaps = total_slots - len(indices)
                    if gaps > 0:
                        soft_conflicts += gaps
                        # This is a minor soft penalty
                        
        fitness = 1.0 / (1.0 + hard_conflicts + 0.1 * soft_conflicts)
        
        return fitness, hard_conflicts, soft_conflicts, {
            'overlap_faculty': overlap_faculty,
            'overlap_room': overlap_room,
            'overlap_group': overlap_group,
            'unavailability_violations': unavailability_violations,
            'soft_gap_violations': soft_gap_violations,
            'soft_dist_violations': soft_dist_violations,
            'conflicted_session_ids': list(conflicted_session_ids)
        }
        
    def tournament_selection(self, k=3):
        # Pick k random individuals and return the best
        selected = random.sample(self.population, k)
        best = max(selected, key=lambda chrom: self.calculate_fitness(chrom)[0])
        return best
        
    def crossover(self, parent1, parent2):
        if random.random() > self.crossover_rate:
            return copy.deepcopy(parent1), copy.deepcopy(parent2)
            
        # Uniform crossover
        child1 = []
        child2 = []
        for g1, g2 in zip(parent1, parent2):
            if random.random() < 0.5:
                child1.append(copy.deepcopy(g1))
                child2.append(copy.deepcopy(g2))
            else:
                child1.append(copy.deepcopy(g2))
                child2.append(copy.deepcopy(g1))
        return child1, child2
        
    def smart_mutate(self, chromosome):
        """
        Performs heuristic mutation. For genes that are in conflict,
        tries to find a conflict-free (day, slot, room).
        If none found, performs a standard random mutation on that gene.
        """
        # Calculate initial fitness details
        _, hard_conf, _, details = self.calculate_fitness(chromosome)
        
        # If there are no hard conflicts, we can just do normal tiny mutation
        if hard_conf == 0:
            for i in range(len(chromosome)):
                if random.random() < self.mutation_rate:
                    chromosome[i] = self.generate_random_gene()
            return chromosome
            
        conflicted_ids = details.get('conflicted_session_ids', [])
        
        for i in range(len(chromosome)):
            session = self.sessions[i]
            is_conflicted = session['id'] in conflicted_ids
            
            # We mutate a gene if the mutation rate is met
            if random.random() < self.mutation_rate:
                if is_conflicted:
                    # Relocate conflict heuristics: search for a better assignment
                    best_gene = chromosome[i]
                    best_conflicts = 9999
                    
                    # Check a few random slots to find a better one
                    test_slots = [self.generate_random_gene() for _ in range(15)]
                        
                    # Evaluate these choices
                    for candidate in test_slots:
                        temp_chrom = list(chromosome)
                        temp_chrom[i] = candidate
                        _, h_conf, s_conf, _ = self.calculate_fitness(temp_chrom)
                        score = h_conf + 0.1 * s_conf
                        if score < best_conflicts:
                            best_conflicts = score
                            best_gene = candidate
                            if score == 0:
                                break # Found perfect placement
                                
                    chromosome[i] = best_gene
                else:
                    # Non-conflicted genes undergo random mutation with lower probability
                    # to maintain diversity without disrupting already correct segments
                    if random.random() < 0.2:
                        chromosome[i] = self.generate_random_gene()
        return chromosome

    def evolve_generation(self):
        # Sort current population by fitness
        scored_pop = [(self.calculate_fitness(chrom)[0], chrom) for chrom in self.population]
        scored_pop.sort(key=lambda x: x[0], reverse=True)
        
        next_pop = []
        # Elitism
        for i in range(min(self.elitism_size, self.pop_size)):
            next_pop.append(copy.deepcopy(scored_pop[i][1]))
            
        # Breed remaining
        while len(next_pop) < self.pop_size:
            p1 = self.tournament_selection()
            p2 = self.tournament_selection()
            
            c1, c2 = self.crossover(p1, p2)
            
            c1 = self.smart_mutate(c1)
            c2 = self.smart_mutate(c2)
            
            next_pop.append(c1)
            if len(next_pop) < self.pop_size:
                next_pop.append(c2)
                
        self.population = next_pop[:self.pop_size]
        
        # Get new best
        best_fitness, best_chrom = max(
            [(self.calculate_fitness(chrom), chrom) for chrom in self.population],
            key=lambda x: x[0][0]
        )
        return best_chrom, best_fitness
