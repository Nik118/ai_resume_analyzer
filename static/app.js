const API_BASE = "http://localhost:8001";
let currentResumes = [];
let currentJobs = [];
let selectedResumeId = null;
let activeJobId = null;

document.addEventListener('DOMContentLoaded', () => {
    fetchResumes();

    document.getElementById('resume-upload').addEventListener('change', handleUpload);
    document.getElementById('btn-roast').addEventListener('click', handleRoast);

    // Tabs
    document.getElementById('tab-overview').addEventListener('click', () => switchTab('overview'));
    document.getElementById('tab-jobs').addEventListener('click', () => switchTab('jobs'));
    document.getElementById('tab-analytics').addEventListener('click', () => switchTab('analytics'));

    // Job Tracker
    document.getElementById('btn-new-job').addEventListener('click', showAddJobView);
    document.getElementById('btn-analyze-job').addEventListener('click', handleAnalyzeJob);
    document.getElementById('btn-delete-job').addEventListener('click', handleDeleteJob);
    
    // Tailoring
    document.getElementById('btn-tailor').addEventListener('click', handleTailor);
    document.getElementById('btn-cover-letter').addEventListener('click', handleCoverLetter);
    document.getElementById('btn-interview').addEventListener('click', handleInterviewPrep);
    document.getElementById('btn-refresh-job').addEventListener('click', async () => {
        if (!activeJobId) return;
        const btn = document.getElementById('btn-refresh-job');
        const originalContent = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        try {
            const response = await fetch(`${API_BASE}/job_targets/${activeJobId}/refresh`, { method: 'POST' });
            if (!response.ok) throw new Error('Failed to refresh job');
            const updatedJob = await response.json();
            const index = currentJobs.findIndex(j => j.id === activeJobId);
            if (index !== -1) {
                currentJobs[index] = updatedJob;
                renderJobsList();
                selectJob(activeJobId);
            }
            showToast('Job refreshed', 'success');
        } catch(e) {
            showToast(e.message, 'error');
        }
        btn.innerHTML = originalContent;
    });
    
    // Kanban Add/Back
    document.getElementById('btn-back-from-add').addEventListener('click', () => {
        document.getElementById('add-job-view').classList.add('hidden');
        document.getElementById('kanban-board-view').classList.remove('hidden');
        document.getElementById('job-detail-container').classList.add('hidden');
    });
    document.getElementById('btn-back-from-job').addEventListener('click', () => {
        document.getElementById('saved-job-view').classList.add('hidden');
        document.getElementById('kanban-board-view').classList.remove('hidden');
        document.getElementById('job-detail-container').classList.add('hidden');
    });
    
    // Analytics
    document.getElementById('btn-refresh-analytics').addEventListener('click', fetchAnalytics);
    
    // Setup Drag and Drop
    setupDragAndDrop();
});

// --- Tabs ---
function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    document.getElementById(`tab-${tab}`).classList.add('active');
    document.getElementById(`view-${tab}`).classList.add('active');

    if (tab === 'jobs' && selectedResumeId) {
        document.getElementById('kanban-board-view').classList.remove('hidden');
        document.getElementById('job-detail-container').classList.add('hidden');
        fetchJobs();
    } else if (tab === 'analytics' && selectedResumeId) {
        fetchAnalytics();
    }
}

// --- API Calls (Resumes) ---

async function fetchResumes() {
    try {
        const response = await fetch(`${API_BASE}/resumes/`);
        if (!response.ok) throw new Error('Failed to fetch resumes');
        currentResumes = await response.json();
        renderResumeList();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const statusEl = document.getElementById('upload-status');
    statusEl.innerHTML = '<div class="loader"></div> Processing...';
    statusEl.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}/resumes/`, { method: 'POST', body: formData });
        if (!response.ok) { const err = await response.json(); throw new Error(err.detail || 'Upload failed'); }
        const newResume = await response.json();
        currentResumes.unshift(newResume);
        renderResumeList();
        selectResume(newResume.id);
        showToast('Resume uploaded!', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        statusEl.classList.add('hidden');
        e.target.value = '';
    }
}

async function deleteResume(id) {
    if(!confirm("Delete this resume and all its saved jobs?")) return;
    try {
        const response = await fetch(`${API_BASE}/resumes/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed to delete');
        
        currentResumes = currentResumes.filter(r => r.id !== id);
        if (selectedResumeId === id) {
            selectedResumeId = null;
            document.getElementById('resume-dashboard').classList.add('hidden');
            document.getElementById('empty-state').classList.add('active');
        }
        renderResumeList();
        showToast('Resume deleted', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// --- API Calls (Jobs) ---

async function fetchJobs() {
    if (!selectedResumeId) return;
    try {
        const response = await fetch(`${API_BASE}/resumes/${selectedResumeId}/jobs`);
        if (!response.ok) throw new Error('Failed to fetch jobs');
        currentJobs = await response.json();
        renderJobsList();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function handleAnalyzeJob() {
    if (!selectedResumeId) return;
    const jd = document.getElementById('jd-input').value.trim();
    const url = document.getElementById('jd-url').value.trim();
    if (!jd) { showToast('Please paste a Job Description', 'error'); return; }

    const btn = document.getElementById('btn-analyze-job');
    btn.innerHTML = '<div class="loader"></div> Analyzing...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/resumes/${selectedResumeId}/jobs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_description: jd, company_url: url || null })
        });
        if (!response.ok) throw new Error('Failed to analyze job');
        const newJob = await response.json();
        
        currentJobs.push(newJob);
        // Re-sort currentJobs by fit score descending
        currentJobs.sort((a, b) => (b.fit_score || 0) - (a.fit_score || 0));
        
        renderJobsList();
        
        document.getElementById('jd-input').value = '';
        document.getElementById('jd-url').value = '';
        selectJob(newJob.id);
        
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-magnifying-glass-chart"></i> Analyze Fit';
        btn.disabled = false;
    }
}

async function handleDeleteJob() {
    if (!activeJobId || !confirm("Delete this job?")) return;
    try {
        const response = await fetch(`${API_BASE}/job_targets/${activeJobId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed to delete job');
        
        currentJobs = currentJobs.filter(j => j.id !== activeJobId);
        document.getElementById('saved-job-view').classList.add('hidden');
        document.getElementById('job-detail-container').classList.add('hidden');
        document.getElementById('kanban-board-view').classList.remove('hidden');
        
        activeJobId = null;
        renderJobsList();
        
        showToast('Job deleted', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Tailoring functions
async function handleTailor() {
    if (!activeJobId) return;
    const btn = document.getElementById('btn-tailor');
    btn.innerHTML = '<div class="loader"></div> Tailoring...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/job_targets/${activeJobId}/tailor`, { method: 'POST' });
        if (!response.ok) throw new Error('Failed to tailor resume');
        const updatedJob = await response.json();
        
        // Update job in list
        const idx = currentJobs.findIndex(j => j.id === activeJobId);
        if (idx !== -1) currentJobs[idx] = updatedJob;
        
        renderTailoredData(updatedJob);
        showToast('Resume Tailored!', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Tailor Resume';
        btn.disabled = false;
    }
}

async function handleCoverLetter() {
    if (!activeJobId) return;
    const btn = document.getElementById('btn-cover-letter');
    btn.innerHTML = '<div class="loader"></div>';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/job_targets/${activeJobId}/cover_letter`, { method: 'POST' });
        if (!response.ok) throw new Error('Failed to generate cover letter');
        const data = await response.json();
        showExtraResults("Cover Letter", data.cover_letter);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-envelope-open-text"></i> Cover';
        btn.disabled = false;
    }
}

async function handleInterviewPrep() {
    if (!activeJobId) return;
    const btn = document.getElementById('btn-interview');
    btn.innerHTML = '<div class="loader"></div>';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/job_targets/${activeJobId}/interview_prep`, { method: 'POST' });
        if (!response.ok) throw new Error('Failed to generate interview prep');
        const data = await response.json();
        const qList = data.questions.map(q => `• ${q}`).join('\n\n');
        showExtraResults("Probable Interview Questions", qList);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-clipboard-question"></i> Prep';
        btn.disabled = false;
    }
}

async function handleRoast() {
    if (!selectedResumeId) return;
    const roastBtn = document.getElementById('btn-roast');
    roastBtn.innerHTML = '<div class="loader"></div> Roasting...';
    roastBtn.disabled = true;
    try {
        const response = await fetch(`${API_BASE}/resumes/${selectedResumeId}/roast`, { method: 'POST' });
        if (!response.ok) throw new Error('Failed to generate roast');
        const data = await response.json();
        document.getElementById('roast-text').innerText = data.roast;
        document.getElementById('roast-container').classList.remove('hidden');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        roastBtn.innerHTML = '<i class="fa-solid fa-fire"></i> Roast Me';
        roastBtn.disabled = false;
    }
}


// --- UI Rendering ---

function renderResumeList() {
    const listEl = document.getElementById('resume-list');
    listEl.innerHTML = '';
    currentResumes.forEach(r => {
        const item = document.createElement('div');
        item.className = `resume-item ${r.id === selectedResumeId ? 'active' : ''}`;
        
        const infoDiv = document.createElement('div');
        infoDiv.innerHTML = `<div style="font-weight: 600;">${r.filename}</div><div style="font-size: 0.8rem; color: var(--text-muted);">${r.experience_years} Years Exp</div>`;
        infoDiv.style.flexGrow = '1';
        infoDiv.onclick = () => selectResume(r.id);
        
        const rightDiv = document.createElement('div');
        rightDiv.style.display = 'flex';
        rightDiv.style.alignItems = 'center';
        rightDiv.style.gap = '10px';
        
        if(r.ats_score) rightDiv.innerHTML += `<div class="score-badge">${r.ats_score}</div>`;
        
        const delBtn = document.createElement('button');
        delBtn.className = 'icon-btn';
        delBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
        delBtn.onclick = (e) => { e.stopPropagation(); deleteResume(r.id); };
        
        rightDiv.appendChild(delBtn);
        
        item.appendChild(infoDiv);
        item.appendChild(rightDiv);
        listEl.appendChild(item);
    });
}

function selectResume(id) {
    selectedResumeId = id;
    renderResumeList();
    
    const resume = currentResumes.find(r => r.id === id);
    if (!resume) return;

    document.getElementById('empty-state').classList.remove('active');
    document.getElementById('resume-dashboard').classList.add('active');
    document.getElementById('dash-title').innerText = resume.filename;

    // Reset Overview
    document.getElementById('roast-container').classList.add('hidden');
    
    const scoreEl = document.getElementById('dash-score');
    scoreEl.innerText = resume.ats_score || '--';
    scoreEl.className = 'score-circle'; 
    if (resume.ats_score >= 80) scoreEl.classList.add('score-excellent');
    else if (resume.ats_score >= 50) scoreEl.classList.add('score-good');
    else scoreEl.classList.add('score-poor');

    const impEl = document.getElementById('dash-improvements');
    impEl.innerHTML = (resume.room_for_improvements || []).map(s => `<li class="bullet-item"><i class="fa-solid fa-circle-right" style="color: var(--accent-secondary)"></i> <span>${s}</span></li>`).join('');

    const strengthsEl = document.getElementById('dash-strengths');
    strengthsEl.innerHTML = (resume.strengths || []).map(s => `<li class="bullet-item"><i class="fa-solid fa-check-circle success-text"></i> <span>${s}</span></li>`).join('');

    const weakEl = document.getElementById('dash-weaknesses');
    weakEl.innerHTML = (resume.weaknesses || []).map(s => `<li class="bullet-item"><i class="fa-solid fa-circle-xmark danger-text"></i> <span>${s}</span></li>`).join('');

    switchTab('overview');
}

function showAddJobView() {
    document.getElementById('kanban-board-view').classList.add('hidden');
    document.getElementById('job-detail-container').classList.remove('hidden');
    document.getElementById('add-job-view').classList.remove('hidden');
    document.getElementById('saved-job-view').classList.add('hidden');
}

async function fetchAnalytics() {
    if (!selectedResumeId) return;
    try {
        const response = await fetch(`${API_BASE}/resumes/${selectedResumeId}/analytics`);
        if (!response.ok) throw new Error('Failed to fetch analytics');
        const data = await response.json();
        
        document.getElementById('analytics-avg-score').innerText = (data.average_fit || 0) + '%';
        
        const list = document.getElementById('analytics-skills-list');
        list.innerHTML = '';
        if(data.missing_skills_freq && data.missing_skills_freq.length > 0) {
            data.missing_skills_freq.forEach(item => {
                list.innerHTML += `<div class="sw-card p-3 flex-between">
                    <span>${item.skill}</span>
                    <span class="badge" style="background:var(--danger); padding:2px 8px; border-radius:12px;">Missing ${item.count}x</span>
                </div>`;
            });
        } else {
            list.innerHTML = '<p class="text-muted">No missing skills found across your jobs.</p>';
        }
    } catch(e) {
        showToast(e.message, 'error');
    }
}

function renderJobsList() {
    // Clear all kanban columns
    const statuses = ['Saved', 'Applied', 'Interviewing', 'Closed'];
    statuses.forEach(s => {
        const col = document.querySelector(`.kanban-dropzone[data-status="${s}"]`);
        if(col) col.innerHTML = '';
    });

    currentJobs.forEach(job => {
        const div = document.createElement('div');
        div.className = 'kanban-card';
        div.setAttribute('draggable', 'true');
        div.dataset.id = job.id;
        
        let scoreColor = job.fit_score >= 80 ? 'var(--success)' : (job.fit_score >= 60 ? 'var(--warning)' : 'var(--danger)');
        div.innerHTML = `
            <h4>${job.company_name || 'Unknown Company'}</h4>
            <div class="score-badge" style="background: ${scoreColor}22; color: ${scoreColor}">${job.fit_score || 0}% Fit</div>
        `;
        
        div.addEventListener('dragstart', handleDragStart);
        div.addEventListener('dragend', handleDragEnd);
        
        div.addEventListener('click', (e) => {
            if(e.target.closest('.kanban-card') === div && !div.classList.contains('dragging')) {
                selectJob(job.id);
            }
        });
        
        const status = job.status || 'Saved';
        const col = document.querySelector(`.kanban-dropzone[data-status="${status}"]`);
        if (col) {
            col.appendChild(div);
        } else {
            document.querySelector('.kanban-dropzone[data-status="Saved"]').appendChild(div);
        }
    });
}

function setupDragAndDrop() {
    const zones = document.querySelectorAll('.kanban-dropzone');
    zones.forEach(zone => {
        zone.addEventListener('dragover', e => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });
        zone.addEventListener('dragleave', e => {
            zone.classList.remove('drag-over');
        });
        zone.addEventListener('drop', async e => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            const dragged = document.querySelector('.kanban-card.dragging');
            if (dragged) {
                zone.appendChild(dragged);
                const jobId = dragged.dataset.id;
                const newStatus = zone.dataset.status;
                
                // Update local array
                const job = currentJobs.find(j => j.id == jobId);
                if (job) job.status = newStatus;
                
                // Update backend
                try {
                    await fetch(`${API_BASE}/job_targets/${jobId}/status`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ status: newStatus })
                    });
                } catch(err) {
                    console.error("Failed to update status", err);
                }
            }
        });
    });
}

function handleDragStart(e) {
    this.classList.add('dragging');
}
function handleDragEnd(e) {
    this.classList.remove('dragging');
}

function selectJob(id) {
    activeJobId = id;
    const job = currentJobs.find(j => j.id === id);
    if (!job) return;
    
    document.getElementById('kanban-board-view').classList.add('hidden');
    document.getElementById('job-detail-container').classList.remove('hidden');
    document.getElementById('add-job-view').classList.add('hidden');
    document.getElementById('saved-job-view').classList.remove('hidden');

    document.getElementById('view-job-title').innerText = job.company_name || "Target Job";
    
    const scoreEl = document.getElementById('view-fit-score');
    scoreEl.innerText = `Score: ${job.fit_score || 0}% Fit`;
    if (job.fit_score >= 80) scoreEl.style.borderColor = 'var(--success)';
    else if (job.fit_score >= 50) scoreEl.style.borderColor = 'orange';
    else scoreEl.style.borderColor = 'var(--danger)';

    const alignedEl = document.getElementById('view-aligned');
    alignedEl.innerHTML = (job.aligned_skills || []).map(s => `<li class="bullet-item"><span>${s}</span></li>`).join('');

    const missingEl = document.getElementById('view-missing');
    missingEl.innerHTML = (job.missing_skills || []).map(s => `<li class="bullet-item"><span>${s}</span></li>`).join('');

    const posEl = document.getElementById('view-jd-pos');
    if (posEl) posEl.innerHTML = (job.jd_positives || []).map(s => `<li class="bullet-item"><span>${s}</span></li>`).join('');

    const negEl = document.getElementById('view-jd-neg');
    if (negEl) negEl.innerHTML = (job.jd_negatives || []).map(s => `<li class="bullet-item"><span>${s}</span></li>`).join('');

    const csEl = document.getElementById('view-company-stability');
    if (csEl) csEl.innerHTML = (job.company_stability_insights || []).map(s => `<li class="bullet-item"><i class="fa-solid fa-angle-right" style="color: var(--accent-secondary)"></i> <span>${s}</span></li>`).join('');

    renderTailoredData(job);
}

function renderTailoredData(job) {
    const resEl = document.getElementById('tailor-results');
    if (job.tailored_summary || (job.tailored_bullets && job.tailored_bullets.length > 0)) {
        resEl.classList.remove('hidden');
        document.getElementById('tailor-summary').innerText = job.tailored_summary || "";
        const bulletsEl = document.getElementById('tailor-bullets');
        bulletsEl.innerHTML = (job.tailored_bullets || []).map(b => `<li class="bullet-item"><i class="fa-solid fa-bolt" style="color: var(--accent-secondary)"></i> <span>${b}</span></li>`).join('');
    } else {
        resEl.classList.add('hidden');
    }
}

function showExtraResults(title, text) {
    const el = document.getElementById('extra-results');
    el.classList.remove('hidden');
    el.innerHTML = `<h4>${title}</h4><div class="extra-box">${text}</div>`;
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation'}"></i> ${message}`;
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(() => { toast.classList.add('fade-out'); setTimeout(() => toast.remove(), 300); }, 4000);
}
