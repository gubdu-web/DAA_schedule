import unittest
from scheduler import parse_dataset, Scheduler

class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.sample_text = """
# DAYS OF THE WEEK
[Days]
Monday, Tuesday

# DAILY TIME SLOTS
[TimeSlots]
09:00-10:00, 10:00-11:00

# CLASSROOMS
[Rooms]
Room 101, Room 102

# FACULTY MEMBERS
[Faculty]
Dr. Smith: Math, Physics
Dr. Jones: Chemistry | Unavailable: Monday 09:00-10:00

# CLASS REQUIREMENTS
[Requirements]
Grade 10: Math, 2, Dr. Smith
Grade 10: Chemistry, 1, Dr. Jones
"""

    def test_parser(self):
        parsed = parse_dataset(self.sample_text)
        
        self.assertEqual(parsed['days'], ['Monday', 'Tuesday'])
        self.assertEqual(parsed['slots'], ['09:00-10:00', '10:00-11:00'])
        self.assertEqual(parsed['rooms'], ['Room 101', 'Room 102'])
        
        self.assertIn('Dr. Smith', parsed['faculty'])
        self.assertIn('Dr. Jones', parsed['faculty'])
        self.assertEqual(parsed['faculty']['Dr. Smith']['subjects'], ['Math', 'Physics'])
        
        # Check unavailability
        self.assertIn(('monday', '09:00-10:00'), parsed['faculty']['Dr. Jones']['unavailable'])
        
        self.assertEqual(len(parsed['requirements']), 2)
        self.assertEqual(parsed['requirements'][0]['group'], 'Grade 10')
        self.assertEqual(parsed['requirements'][0]['hours'], 2)
        self.assertEqual(parsed['requirements'][0]['preferred_faculty'], 'Dr. Smith')

    def test_scheduler_init(self):
        parsed = parse_dataset(self.sample_text)
        scheduler = Scheduler(parsed)
        
        # Total sessions = 2 (Math) + 1 (Chemistry) = 3 sessions
        self.assertEqual(len(scheduler.sessions), 3)
        self.assertEqual(scheduler.sessions[0]['subject'], 'Math')
        self.assertEqual(scheduler.sessions[1]['subject'], 'Math')
        self.assertEqual(scheduler.sessions[2]['subject'], 'Chemistry')
        
        # Initialize population
        scheduler.initialize_population()
        self.assertEqual(len(scheduler.population), scheduler.pop_size)
        
        # Check first chromosome structure
        chrom = scheduler.population[0]
        self.assertEqual(len(chrom), 3)
        self.assertIn(chrom[0]['day'], scheduler.days)
        self.assertIn(chrom[0]['slot'], scheduler.slots)
        self.assertIn(chrom[0]['room'], scheduler.rooms)

    def test_scheduler_fitness(self):
        parsed = parse_dataset(self.sample_text)
        scheduler = Scheduler(parsed)
        scheduler.initialize_population()
        
        chrom = scheduler.population[0]
        fitness, hard, soft, details = scheduler.calculate_fitness(chrom)
        
        self.assertGreater(fitness, 0)
        self.assertGreaterEqual(hard, 0)
        self.assertGreaterEqual(soft, 0)
        self.assertIsInstance(details, dict)
        self.assertIn('overlap_faculty', details)

    def test_scheduler_evolution(self):
        parsed = parse_dataset(self.sample_text)
        scheduler = Scheduler(parsed, pop_size=10, mutation_rate=0.2)
        scheduler.initialize_population()
        
        # Evolve for 5 generations
        for _ in range(5):
            best_chrom, (fitness, hard, soft, details) = scheduler.evolve_generation()
            
        self.assertGreater(fitness, 0)
        self.assertEqual(len(best_chrom), len(scheduler.sessions))

if __name__ == '__main__':
    unittest.main()
