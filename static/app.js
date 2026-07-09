// Sample dataset for instant loading
const SAMPLE_DATASET = `# DAYS OF THE WEEK
[Days]
Monday, Tuesday, Wednesday, Thursday, Friday

# DAILY TIME SLOTS
[TimeSlots]
09:00-10:00, 10:00-11:00, 11:00-12:00, 13:00-14:00, 14:00-15:00

# CLASSROOMS
[Rooms]
Room 101, Room 102, Room 103

# FACULTY MEMBERS (Name: Subject1, Subject2... [Unavailable: Day Slot, Day Slot...])
[Faculty]
Dr. Smith: Math, Physics
Dr. Jones: Chemistry, Biology | Unavailable: Monday 09:00-10:00, Wednesday 10:00-11:00
Dr. Taylor: History, English
Prof. Davis: Computer Science

# CLASS REQUIREMENTS (Student Group: Subject, Weekly Hours, Preferred Faculty)
[Requirements]
Grade 10: Math, 3, Dr. Smith
Grade 10: Physics, 2, Dr. Smith
Grade 10: Chemistry, 2, Dr. Jones
Grade 10: English, 2, Dr. Taylor
Grade 10: Computer Science, 2, Prof. Davis
Grade 11: Math, 3, Dr. Smith
Grade 11: Biology, 2, Dr. Jones
Grade 11: History, 2, Dr. Taylor
Grade 11: Computer Science, 3, Prof. Davis`;

// Global State
let parsedData = null;
let currentSchedule = null;
let pollInterval = null;
let progressChart = null;
let currentView = 'group'; // 'group', 'faculty', 'room'
let selectedFilterValue = '';

// DOM Elements
const datasetInput = document.getElementById('dataset-input');
const fileDropZone = document.getElementById('file-drop-zone');
const fileLoader = document.getElementById('file-loader');
const loadSampleBtn = document.getElementById('load-sample-btn');
const clearInputBtn = document.getElementById('clear-input-btn');
const landingLoadBtn = document.getElementById('landing-load-btn');

const popSizeSlider = document.getElementById('pop-size');
const popSizeVal = document.getElementById('pop-size-val');
const mutationRateSlider = document.getElementById('mutation-rate');
const mutationRateVal = document.getElementById('mutation-rate-val');
const maxGenerationsSlider = document.getElementById('max-generations');
const maxGenerationsVal = document.getElementById('max-generations-val');

const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');

const sumDays = document.getElementById('sum-days');
const sumSlots = document.getElementById('sum-slots');
const sumRooms = document.getElementById('sum-rooms');
const sumFaculty = document.getElementById('sum-faculty');
const sumGroups = document.getElementById('sum-groups');
const sumSessions = document.getElementById('sum-sessions');

const warningsArea = document.getElementById('warnings-area');
const warningsList = document.getElementById('warnings-list');

const progressPanel = document.getElementById('progress-panel');
const resultsPanel = document.getElementById('results-panel');
const landingPanel = document.getElementById('landing-panel');

const statusIndicator = document.getElementById('status-indicator');
const progressBarFill = document.getElementById('progress-bar-fill');
const statGen = document.getElementById('stat-gen');
const statFitness = document.getElementById('stat-fitness');
const statHardConf = document.getElementById('stat-hard-conf');
const statSoftConf = document.getElementById('stat-soft-conf');
const hardConflictCard = document.getElementById('hard-conflict-card');

const viewToggle = document.getElementById('view-toggle');
const filterSelect = document.getElementById('filter-select');
const scheduleTable = document.getElementById('schedule-table');
const tableHeadRow = document.getElementById('table-head-row');
const tableBody = document.getElementById('table-body');
const exportBtn = document.getElementById('export-btn');

const conflictsBreakdown = document.getElementById('conflicts-breakdown');
const totalConflictCount = document.getElementById('total-conflict-count');
const hardConflictsList = document.getElementById('hard-conflicts-list');
const softConflictsList = document.getElementById('soft-conflicts-list');

// Initialize App
window.addEventListener('DOMContentLoaded', () => {
    setupSliders();
    setupDropzone();
    setupEventListeners();
    initChart();
    
    // Automatically trigger initial parsing if there's text
    if (datasetInput.value.trim()) {
        parseDatasetText();
    }
});

// Setup Slider Value Displays
function setupSliders() {
    popSizeSlider.addEventListener('input', () => {
        popSizeVal.textContent = popSizeSlider.value;
    });
    
    mutationRateSlider.addEventListener('input', () => {
        mutationRateVal.textContent = Math.round(mutationRateSlider.value * 100) + '%';
    });
    
    maxGenerationsSlider.addEventListener('input', () => {
        maxGenerationsVal.textContent = maxGenerationsSlider.value;
    });
}

// Setup Event Listeners
function setupEventListeners() {
    loadSampleBtn.addEventListener('click', () => loadSample(SAMPLE_DATASET));
    landingLoadBtn.addEventListener('click', () => loadSample(SAMPLE_DATASET));
    
    clearInputBtn.addEventListener('click', () => {
        datasetInput.value = '';
        parseDatasetText();
    });
    
    datasetInput.addEventListener('input', debounce(parseDatasetText, 500));
    
    startBtn.addEventListener('click', startScheduling);
    stopBtn.addEventListener('click', stopScheduling);
    
    // File upload browsing
    fileDropZone.addEventListener('click', () => fileLoader.click());
    fileLoader.addEventListener('change', handleFileSelect);
    
    // Filter toggles
    viewToggle.addEventListener('click', (e) => {
        if (e.target.classList.contains('toggle-btn')) {
            document.querySelectorAll('#view-toggle .toggle-btn').forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
            currentView = e.target.dataset.view;
            updateFilterDropdown();
            renderScheduleGrid();
        }
    });
    
    filterSelect.addEventListener('change', (e) => {
        selectedFilterValue = e.target.value;
        renderScheduleGrid();
    });
    
    exportBtn.addEventListener('click', exportScheduleCSV);
}

// Setup Drag & Drop dataset uploads
function setupDropzone() {
    const container = datasetInput.parentElement;
    
    datasetInput.addEventListener('dragenter', (e) => {
        e.preventDefault();
        container.classList.add('dragover');
    });
    
    fileDropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        container.classList.remove('dragover');
    });
    
    fileDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
    });
    
    fileDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        container.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.name.endsWith('.txt')) {
                readFile(file);
            } else {
                alert('Please upload a valid plain text (.txt) file.');
            }
        }
    });
}

function handleFileSelect(e) {
    if (e.target.files.length > 0) {
        readFile(e.target.files[0]);
    }
}

function readFile(file) {
    const reader = new FileReader();
    reader.onload = (event) => {
        datasetInput.value = event.target.result;
        parseDatasetText();
    };
    reader.readAsText(file);
}

function loadSample(text) {
    datasetInput.value = text;
    parseDatasetText();
}

// Debounce helper
function debounce(func, wait) {
    let timeout;
    return functionExecuted = (...args) => {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Parse input text using backend REST API
async function parseDatasetText() {
    const text = datasetInput.value.trim();
    if (!text) {
        resetParseStats();
        return;
    }
    
    try {
        const response = await fetch('/api/parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        const result = await response.json();
        
        if (result.success) {
            parsedData = result.data;
            updateParseStats(result.data, result.warnings);
            startBtn.disabled = false;
        } else {
            parsedData = null;
            resetParseStats(result.error);
            startBtn.disabled = true;
        }
    } catch (err) {
        console.error('Parsing API error:', err);
        parsedData = null;
        resetParseStats('Failed to connect to parser server.');
        startBtn.disabled = true;
    }
}

function updateParseStats(data, warnings) {
    sumDays.textContent = data.days.length;
    sumSlots.textContent = data.slots.length;
    sumRooms.textContent = data.rooms.length;
    sumFaculty.textContent = data.faculty_count;
    
    // Unique Student Groups
    const groups = new Set(data.requirements.map(r => r.group));
    sumGroups.textContent = groups.size;
    sumSessions.textContent = data.total_sessions;
    
    // Manage warnings
    warningsList.innerHTML = '';
    if (warnings && warnings.length > 0) {
        warnings.forEach(warn => {
            const li = document.createElement('li');
            li.textContent = warn;
            warningsList.appendChild(li);
        });
        warningsArea.classList.remove('hidden');
    } else {
        warningsArea.classList.add('hidden');
    }
}

function resetParseStats(errorMessage = null) {
    sumDays.textContent = '-';
    sumSlots.textContent = '-';
    sumRooms.textContent = '-';
    sumFaculty.textContent = '-';
    sumGroups.textContent = '-';
    sumSessions.textContent = '-';
    
    warningsList.innerHTML = '';
    if (errorMessage) {
        const li = document.createElement('li');
        li.textContent = errorMessage;
        li.className = 'text-danger';
        warningsList.appendChild(li);
        warningsArea.classList.remove('hidden');
    } else {
        warningsArea.classList.add('hidden');
    }
    startBtn.disabled = true;
}

// Start scheduling process
async function startScheduling() {
    const text = datasetInput.value.trim();
    if (!text || !parsedData) return;
    
    const popSize = parseInt(popSizeSlider.value);
    const mutationRate = parseFloat(mutationRateSlider.value);
    const maxGenerations = parseInt(maxGenerationsSlider.value);
    
    // Toggle state to active
    startBtn.classList.add('hidden');
    stopBtn.classList.remove('hidden');
    
    progressPanel.classList.remove('hidden');
    landingPanel.classList.add('hidden');
    
    // Reset local optimization monitor displays
    progressBarFill.style.width = '0%';
    statGen.textContent = `0 / ${maxGenerations}`;
    statFitness.textContent = '0.00%';
    statHardConf.textContent = '0';
    statSoftConf.textContent = '0';
    hardConflictCard.classList.remove('active-conflicts');
    
    // Clear and reset progress chart
    resetChart(maxGenerations);
    
    try {
        const response = await fetch('/api/schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                pop_size: popSize,
                mutation_rate: mutationRate,
                max_generations: maxGenerations
            })
        });
        
        const result = await response.json();
        if (result.success) {
            updateStatusIndicator('running', 'Running Genetic Algorithm...');
            
            // Start Polling loop
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(pollProgress, 180);
        } else {
            alert(result.error || 'Failed to start scheduler.');
            stopSchedulingUI();
        }
    } catch (err) {
        console.error('Failed to start scheduling:', err);
        alert('Network error connecting to scheduling engine.');
        stopSchedulingUI();
    }
}

// Stop scheduling process
async function stopScheduling() {
    try {
        await fetch('/api/schedule/stop', { method: 'POST' });
        updateStatusIndicator('stopped', 'Stopping algorithm...');
    } catch (err) {
        console.error('Error requesting scheduler stop:', err);
    }
}

function stopSchedulingUI() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
    startBtn.classList.remove('hidden');
    stopBtn.classList.add('hidden');
}

// Poll Progress API
async function pollProgress() {
    try {
        const response = await fetch('/api/schedule/progress');
        const result = await response.json();
        
        if (!result.success) return;
        
        const progress = result.progress;
        const gen = progress.generation;
        const maxGen = progress.max_generations;
        const hard = progress.hard_conflicts;
        const soft = progress.soft_conflicts;
        const fitness = progress.best_fitness;
        const status = progress.status;
        
        // Update stats
        statGen.textContent = `${gen} / ${maxGen}`;
        statFitness.textContent = `${(fitness * 100).toFixed(2)}%`;
        statHardConf.textContent = hard;
        statSoftConf.textContent = soft.toFixed(1);
        
        const pct = Math.round((gen / maxGen) * 100);
        progressBarFill.style.width = `${pct}%`;
        
        // Conflict card highlight
        if (hard > 0) {
            hardConflictCard.classList.add('active-conflicts');
        } else {
            hardConflictCard.classList.remove('active-conflicts');
        }
        
        // Push stats to line chart
        addChartData(gen, hard, soft);
        
        updateStatusIndicator(status, getStatusLabel(status, hard));
        
        // Update current schedule
        if (progress.best_schedule) {
            currentSchedule = progress.best_schedule;
            
            // Only update schedule grid and filters live if they aren't fully completed yet,
            // or just render it once at the end to save browser repaint cycles.
            // Let's render every few generations or only at the end.
            // Rendering on every generation is nice, let's render it live!
            if (gen % 5 === 0 || status !== 'running') {
                if (!filterSelect.options.length) {
                    updateFilterDropdown();
                }
                renderScheduleGrid();
                renderConflictsList(progress.conflict_details);
            }
        }
        
        // Check if finished
        if (status === 'completed' || status === 'stopped' || status === 'error') {
            stopSchedulingUI();
            
            if (status === 'error') {
                alert(`Scheduler crashed: ${progress.error_message}`);
            }
            
            // Final render
            updateFilterDropdown();
            renderScheduleGrid();
            renderConflictsList(progress.conflict_details);
            
            resultsPanel.classList.remove('hidden');
        }
    } catch (err) {
        console.error('Polling error:', err);
    }
}

function getStatusLabel(status, hardConflicts) {
    if (status === 'running') {
        return hardConflicts === 0 
            ? 'Optimizing soft constraints...' 
            : 'Searching conflict-free spaces...';
    }
    if (status === 'completed') {
        return hardConflicts === 0 
            ? 'Success! Valid Schedule Generated.' 
            : 'Completed. Schedule has conflicts.';
    }
    if (status === 'stopped') {
        return 'Algorithm Stopped by User.';
    }
    if (status === 'error') {
        return 'Execution Failed.';
    }
    return 'Active';
}

function updateStatusIndicator(status, message) {
    // Reset indicator classes
    statusIndicator.className = 'status-indicator';
    statusIndicator.classList.add(`status-${status}`);
    statusIndicator.querySelector('.indicator-text').textContent = message;
}

// Dropdown filter population
function updateFilterDropdown() {
    if (!parsedData) return;
    
    const prevSelected = filterSelect.value;
    filterSelect.innerHTML = '';
    
    let items = [];
    if (currentView === 'group') {
        // Collect all student groups
        const groups = new Set(parsedData.requirements.map(r => r.group));
        items = Array.from(groups).sort();
    } else if (currentView === 'faculty') {
        // Collect faculty names from parsedData
        items = Object.keys(parsedData.faculty).sort();
    } else if (currentView === 'room') {
        items = [...parsedData.rooms].sort();
    }
    
    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item;
        opt.textContent = item;
        filterSelect.appendChild(opt);
    });
    
    // Restore selection if possible, otherwise pick first
    if (items.includes(prevSelected)) {
        filterSelect.value = prevSelected;
    }
    
    selectedFilterValue = filterSelect.value;
}

// Render schedule grid
function renderScheduleGrid() {
    if (!currentSchedule || !parsedData || !selectedFilterValue) {
        tableBody.innerHTML = `<tr><td colspan="${parsedData ? parsedData.days.length + 1 : 1}" class="empty-cell">No schedule available</td></tr>`;
        return;
    }
    
    const days = parsedData.days;
    const slots = parsedData.slots;
    
    // 1. Draw table head days
    tableHeadRow.innerHTML = '<th>Time Slot</th>';
    days.forEach(day => {
        const th = document.createElement('th');
        th.textContent = day;
        tableHeadRow.appendChild(th);
    });
    
    // 2. Build rows for each slot
    tableBody.innerHTML = '';
    
    slots.forEach(slot => {
        const tr = document.createElement('tr');
        
        // Slot label column
        const tdSlotLabel = document.createElement('td');
        tdSlotLabel.innerHTML = `<strong>${slot}</strong>`;
        tr.appendChild(tdSlotLabel);
        
        // Day columns
        days.forEach(day => {
            const td = document.createElement('td');
            
            // Find matches in the schedule for this (day, slot) and active filter
            const matches = currentSchedule.filter(item => {
                const dayMatch = item.day.toLowerCase() === day.toLowerCase();
                const slotMatch = item.slot.toLowerCase() === slot.toLowerCase();
                if (!dayMatch || !slotMatch) return false;
                
                if (currentView === 'group') {
                    return item.group === selectedFilterValue;
                } else if (currentView === 'faculty') {
                    return item.faculty === selectedFilterValue;
                } else if (currentView === 'room') {
                    return item.room === selectedFilterValue;
                }
                return false;
            });
            
            if (matches.length > 0) {
                // If there are multiple matches in this slot (e.g. room double booked or group double booked),
                // render them stacked to visually show conflicts!
                matches.forEach(match => {
                    const block = document.createElement('div');
                    block.className = 'slot-block';
                    
                    if (currentView === 'group') {
                        block.innerHTML = `
                            <span class="slot-subject">${match.subject}</span>
                            <span class="slot-sub-info">${match.faculty || 'No Faculty'}</span>
                            <span class="slot-meta">${match.room}</span>
                        `;
                    } else if (currentView === 'faculty') {
                        block.innerHTML = `
                            <span class="slot-subject">${match.subject}</span>
                            <span class="slot-sub-info">${match.group}</span>
                            <span class="slot-meta">${match.room}</span>
                        `;
                    } else if (currentView === 'room') {
                        block.innerHTML = `
                            <span class="slot-subject">${match.subject}</span>
                            <span class="slot-sub-info">${match.group}</span>
                            <span class="slot-meta">${match.faculty || 'No Faculty'}</span>
                        `;
                    }
                    td.appendChild(block);
                });
            } else {
                td.innerHTML = '<div class="empty-cell">-</div>';
            }
            
            tr.appendChild(td);
        });
        
        tableBody.appendChild(tr);
    });
}

// Render conflicts lists
function renderConflictsList(details) {
    if (!details) {
        conflictsBreakdown.classList.add('hidden');
        return;
    }
    
    hardConflictsList.innerHTML = '';
    softConflictsList.innerHTML = '';
    
    const hardItems = [
        ...details.overlap_faculty,
        ...details.overlap_room,
        ...details.overlap_group,
        ...details.unavailability_violations
    ];
    
    const softItems = [
        ...details.soft_gap_violations,
        ...details.soft_dist_violations
    ];
    
    const totalCount = hardItems.length + softItems.length;
    totalConflictCount.textContent = totalCount;
    
    if (totalCount > 0) {
        conflictsBreakdown.classList.remove('hidden');
        
        if (hardItems.length > 0) {
            hardItems.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item;
                hardConflictsList.appendChild(li);
            });
        } else {
            hardConflictsList.innerHTML = '<li style="border-left-color: var(--emerald); font-style: italic;">No hard conflicts. Schedule is valid!</li>';
        }
        
        if (softItems.length > 0) {
            softItems.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item;
                softConflictsList.appendChild(li);
            });
        } else {
            softConflictsList.innerHTML = '<li style="border-left-color: var(--emerald); font-style: italic;">No soft penalties. Schedule is fully distributed!</li>';
        }
    } else {
        conflictsBreakdown.classList.add('hidden');
    }
}

// Initialize Chart.js
function initChart() {
    const ctx = document.getElementById('fitness-chart').getContext('2d');
    
    // Set custom grid lines colors and font styling for dark look
    Chart.defaults.color = 'rgba(255, 255, 255, 0.6)';
    Chart.defaults.font.family = "'Inter', sans-serif";
    
    progressChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Hard Conflicts',
                    data: [],
                    borderColor: '#EF4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 2,
                    tension: 0.15,
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'Soft Penalties',
                    data: [],
                    borderColor: '#F59E0B',
                    backgroundColor: 'transparent',
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                    tension: 0.15,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 10,
                        font: { size: 10 }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Generation', font: { size: 9 } },
                    grid: { color: 'rgba(255, 255, 255, 0.04)' }
                },
                y: {
                    position: 'left',
                    title: { display: true, text: 'Hard Overlaps', font: { size: 9 } },
                    grid: { color: 'rgba(255, 255, 255, 0.06)' },
                    min: 0,
                    ticks: { precision: 0 }
                },
                y1: {
                    position: 'right',
                    title: { display: true, text: 'Soft Penalties', font: { size: 9 } },
                    grid: { drawOnChartArea: false }, // avoid duplicate gridlines
                    min: 0
                }
            }
        }
    });
}

function resetChart(maxGenerations) {
    if (!progressChart) return;
    progressChart.data.labels = [];
    progressChart.data.datasets[0].data = [];
    progressChart.data.datasets[1].data = [];
    progressChart.options.scales.x.max = maxGenerations;
    progressChart.update();
}

function addChartData(generation, hardConflicts, softConflicts) {
    if (!progressChart) return;
    
    // Simple decimation to avoid overcrowded charts on high generation counts
    const totalPoints = progressChart.data.labels.length;
    if (totalPoints > 40 && generation % Math.ceil(generation / 20) !== 0 && generation !== 1) {
        // Keep the best resolutions and ignore mid points to keep rendering smooth
        return;
    }
    
    progressChart.data.labels.push(generation);
    progressChart.data.datasets[0].data.push(hardConflicts);
    progressChart.data.datasets[1].data.push(softConflicts);
    progressChart.update('none'); // Update without animation for raw speed
}

// Export schedule to CSV
function exportScheduleCSV() {
    if (!currentSchedule || currentSchedule.length === 0) return;
    
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Student Group,Subject,Faculty Member,Day,Time Slot,Classroom\n";
    
    // Sort schedule logically before export (Group -> Day -> Slot)
    const sorted = [...currentSchedule].sort((a, b) => {
        if (a.group !== b.group) return a.group.localeCompare(b.group);
        if (a.day !== b.day) return a.day.localeCompare(b.day);
        return a.slot.localeCompare(b.slot);
    });
    
    sorted.forEach(row => {
        const line = `"${row.group}","${row.subject}","${row.faculty || ''}","${row.day}","${row.slot}","${row.room}"`;
        csvContent += line + "\n";
    });
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `optimized_schedule_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
