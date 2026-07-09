import threading
import time
from flask import Flask, request, jsonify, send_from_directory
from scheduler import parse_dataset, Scheduler

app = Flask(__name__, static_folder='static', static_url_path='')

# Global thread-safe state for the active scheduling task
task_lock = threading.Lock()
current_task = {
    'running': False,
    'thread': None,
    'stop_requested': False,
    'progress': {
        'generation': 0,
        'max_generations': 100,
        'best_fitness': 0.0,
        'hard_conflicts': 0,
        'soft_conflicts': 0,
        'conflict_details': {
            'overlap_faculty': [],
            'overlap_room': [],
            'overlap_group': [],
            'unavailability_violations': [],
            'soft_gap_violations': [],
            'soft_dist_violations': []
        },
        'best_schedule': None,
        'status': 'idle',
        'error_message': None
    }
}

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/parse', methods=['POST'])
def parse_endpoint():
    data = request.get_json() or {}
    text = data.get('text', '')
    if not text.strip():
        return jsonify({'success': False, 'error': 'Dataset is empty.'}), 400
    
    try:
        parsed = parse_dataset(text)
        # Calculate some summary stats
        total_sessions = sum(req['hours'] for req in parsed['requirements'])
        
        # Verify validation warnings/checks
        warnings = []
        if not parsed['days']:
            warnings.append("No days defined in the dataset.")
        if not parsed['slots']:
            warnings.append("No time slots defined in the dataset.")
        if not parsed['rooms']:
            warnings.append("No classrooms/rooms defined in the dataset.")
        if not parsed['requirements']:
            warnings.append("No class requirements defined to schedule.")
            
        # Verify that for each requirement, the preferred faculty actually exists
        for req in parsed['requirements']:
            pref_fac = req['preferred_faculty']
            if pref_fac and pref_fac not in parsed['faculty']:
                warnings.append(f"Faculty member '{pref_fac}' is preferred for {req['group']} - {req['subject']}, but not defined in [Faculty].")
            
        return jsonify({
            'success': True,
            'data': {
                'days': parsed['days'],
                'slots': parsed['slots'],
                'rooms': parsed['rooms'],
                'faculty_count': len(parsed['faculty']),
                'requirements_count': len(parsed['requirements']),
                'total_sessions': total_sessions,
                'requirements': parsed['requirements']
            },
            'warnings': warnings
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f"Parsing error: {str(e)}"}), 500

def run_scheduling(dataset, pop_size, mutation_rate, max_generations):
    global current_task
    try:
        scheduler = Scheduler(
            dataset,
            pop_size=pop_size,
            mutation_rate=mutation_rate
        )
        scheduler.initialize_population()
        
        # If there are no sessions to schedule, complete immediately
        if not scheduler.sessions:
            with task_lock:
                current_task['progress']['status'] = 'completed'
                current_task['progress']['best_schedule'] = []
                current_task['running'] = False
            return

        for gen in range(1, max_generations + 1):
            # Check if stop was requested
            with task_lock:
                if current_task['stop_requested']:
                    current_task['progress']['status'] = 'stopped'
                    current_task['running'] = False
                    break
            
            best_chrom, (fitness, hard_conf, soft_conf, details) = scheduler.evolve_generation()
            
            # Format best schedule for frontend
            formatted_schedule = []
            for idx, gene in enumerate(best_chrom):
                session = scheduler.sessions[idx]
                formatted_schedule.append({
                    'group': session['group'],
                    'subject': session['subject'],
                    'faculty': session['faculty'],
                    'day': gene['day'],
                    'slot': gene['slot'],
                    'room': gene['room']
                })
                
            with task_lock:
                current_task['progress']['generation'] = gen
                current_task['progress']['best_fitness'] = fitness
                current_task['progress']['hard_conflicts'] = hard_conf
                current_task['progress']['soft_conflicts'] = soft_conf
                current_task['progress']['conflict_details'] = details
                current_task['progress']['best_schedule'] = formatted_schedule
                
                # If we've reached a valid schedule (0 hard conflicts) and we're at least
                # a few generations in, we can stop early.
                # To make it visual, let's stop only if hard conflicts are 0.
                if hard_conf == 0:
                    current_task['progress']['status'] = 'completed'
                    current_task['running'] = False
                    break
                    
            # Speed simulation to let frontend catch up with progress bars
            time.sleep(0.04)
        else:
            with task_lock:
                current_task['progress']['status'] = 'completed'
                current_task['running'] = False
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        with task_lock:
            current_task['progress']['status'] = 'error'
            current_task['progress']['error_message'] = str(e)
            current_task['running'] = False

@app.route('/api/schedule', methods=['POST'])
def start_schedule():
    global current_task
    
    with task_lock:
        if current_task['running']:
            return jsonify({
                'success': False,
                'error': 'A scheduling process is already running. Please wait or stop it first.'
            }), 400
            
    data = request.get_json() or {}
    text = data.get('text', '')
    pop_size = int(data.get('pop_size', 50))
    mutation_rate = float(data.get('mutation_rate', 0.2))
    max_generations = int(data.get('max_generations', 150))
    
    if not text.strip():
        return jsonify({'success': False, 'error': 'Dataset text is empty.'}), 400
        
    try:
        parsed = parse_dataset(text)
        
        with task_lock:
            current_task['running'] = True
            current_task['stop_requested'] = False
            current_task['progress'] = {
                'generation': 0,
                'max_generations': max_generations,
                'best_fitness': 0.0,
                'hard_conflicts': 9999,
                'soft_conflicts': 9999,
                'conflict_details': {
                    'overlap_faculty': [],
                    'overlap_room': [],
                    'overlap_group': [],
                    'unavailability_violations': [],
                    'soft_gap_violations': [],
                    'soft_dist_violations': []
                },
                'best_schedule': None,
                'status': 'running',
                'error_message': None
            }
            
            # Spawn scheduling thread
            thread = threading.Thread(
                target=run_scheduling,
                args=(parsed, pop_size, mutation_rate, max_generations)
            )
            current_task['thread'] = thread
            thread.start()
            
        return jsonify({'success': True, 'message': 'Scheduling started.'})
    except Exception as e:
        return jsonify({'success': False, 'error': f"Failed to start: {str(e)}"}), 500

@app.route('/api/schedule/progress', methods=['GET'])
def schedule_progress():
    with task_lock:
        return jsonify({
            'success': True,
            'running': current_task['running'],
            'progress': current_task['progress']
        })

@app.route('/api/schedule/stop', methods=['POST'])
def stop_schedule():
    global current_task
    with task_lock:
        if current_task['running']:
            current_task['stop_requested'] = True
            return jsonify({'success': True, 'message': 'Stop requested.'})
        else:
            return jsonify({'success': False, 'error': 'No scheduling process is active.'}), 400

if __name__ == '__main__':
    print("Starting School Timetable Server at http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
