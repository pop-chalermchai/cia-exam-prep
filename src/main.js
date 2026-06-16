import './style.css';

// State Variables
let masterQuestions = [];      // All questions loaded from JSON
let activeQuestions = [];      // Current subset of questions for the active test
let currentQuestionIndex = 0;
let userAnswers = [];          // User selected option indices (null if not answered)
let flaggedQuestions = [];     // Array of booleans tracking flagged questions
let answeredOptionsLocked = []; // In Practice Mode, lock options after first click
let isRealExamMode = false;
let examTimerInterval = null;
let examTimeRemaining = 0;    // Seconds remaining
let examTimeTotal = 0;        // Total duration in seconds
let examTimeSpent = 0;        // Seconds spent
let currentLanguageMode = 'both'; // 'both', 'en', 'th'
let currentPart = 1;          // Selected exam part (1 or 2)

// Selectors
const screens = {
  home: document.getElementById('home-screen'),
  exam: document.getElementById('exam-screen'),
  review: document.getElementById('review-screen')
};

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  setupTheme();
  setupLanguageToggle();
  await loadQuestions();
  setupEventListeners();
  renderStats();
  
  // Initialize Lucide icons
  if (window.lucide) {
    window.lucide.createIcons();
  }
});

// 1. Theme Configuration
function setupTheme() {
  const savedTheme = localStorage.getItem('cia-theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  
  const themeToggle = document.getElementById('theme-toggle');
  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('cia-theme', newTheme);
  });
}

// 2. Language View Setup
function setupLanguageToggle() {
  const savedLangMode = localStorage.getItem('cia-lang-mode') || 'both';
  setLanguageMode(savedLangMode);

  const langBtns = document.querySelectorAll('.lang-view-btn');
  langBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.langMode;
      setLanguageMode(mode);
    });
  });
}

function setLanguageMode(mode) {
  currentLanguageMode = mode;
  localStorage.setItem('cia-lang-mode', mode);
  
  // Update HTML data-lang-mode attribute
  document.body.setAttribute('data-lang-mode', mode);
  
  // Update active button styles
  const langBtns = document.querySelectorAll('.lang-view-btn');
  langBtns.forEach(btn => {
    if (btn.dataset.langMode === mode) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

// 3. Question Bank Loading
async function loadQuestions() {
  try {
    // Try to load full questions file first, fallback to mock questions
    let response;
    try {
      response = await fetch(`/data/questions_part${currentPart}.json`);
      if (!response.ok) throw new Error('Full questions not found');
    } catch {
      response = await fetch('/data/mock_questions.json');
    }
    
    if (response.ok) {
      masterQuestions = await response.json();
      console.log(`Loaded ${masterQuestions.length} questions successfully for Part ${currentPart}.`);
    } else {
      console.error('Failed to load questions JSON files.');
    }
  } catch (error) {
    console.error('Error loading questions:', error);
  }
}

// Switch Exam Part (Part 1 or Part 2)
async function switchPart(partNum) {
  if (currentPart === partNum) return;
  currentPart = partNum;
  
  const part1Btn = document.getElementById('part-select-1');
  const part2Btn = document.getElementById('part-select-2');
  
  if (partNum === 1) {
    if (part1Btn) part1Btn.classList.add('active');
    if (part2Btn) part2Btn.classList.remove('active');
  } else {
    if (part1Btn) part1Btn.classList.remove('active');
    if (part2Btn) part2Btn.classList.add('active');
  }
  
  await loadQuestions();
}

// 4. Set Up Event Listeners
function setupEventListeners() {
  // Navigation Logo Button -> Home
  document.getElementById('nav-logo-btn').addEventListener('click', () => {
    confirmExitToHome();
  });

  // Part selection card clicks
  const part1Btn = document.getElementById('part-select-1');
  const part2Btn = document.getElementById('part-select-2');
  if (part1Btn && part2Btn) {
    part1Btn.addEventListener('click', () => switchPart(1));
    part2Btn.addEventListener('click', () => switchPart(2));
  }

  // Practice Mode Buttons (10, 30, 60, 90, 125)
  const practiceBtns = document.querySelectorAll('.start-practice-btn');
  practiceBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const count = parseInt(btn.dataset.questions, 10);
      startExamSession(count, false);
    });
  });

  // Real Exam Mode Button
  document.getElementById('start-real-exam').addEventListener('click', () => {
    startExamSession(125, true);
  });

  // Exam Screen: Quit Button
  document.getElementById('exam-quit-btn').addEventListener('click', () => {
    confirmExitToHome();
  });

  // Exam Screen: Nav buttons
  document.getElementById('prev-question-btn').addEventListener('click', showPreviousQuestion);
  document.getElementById('next-question-btn').addEventListener('click', showNextQuestion);
  
  // Flag Question Button
  document.getElementById('flag-question-btn').addEventListener('click', toggleFlagCurrentQuestion);

  // Submit Exam Button
  document.getElementById('submit-exam-btn').addEventListener('click', () => {
    const unansweredCount = userAnswers.filter(ans => ans === null).length;
    let message = 'คุณต้องการส่งกระดาษคำตอบใช่หรือไม่?';
    if (unansweredCount > 0) {
      message = `คุณยังไม่ได้ทำข้อสอบอีก ${unansweredCount} ข้อ ต้องการส่งคำตอบเลยใช่หรือไม่?`;
    }
    if (confirm(message)) {
      submitExam();
    }
  });

  // Review Screen: Back to Home
  document.getElementById('review-go-home-btn').addEventListener('click', () => {
    switchScreen('home');
  });

  // Review Screen: Scroll to details
  document.getElementById('scroll-to-review-details-btn').addEventListener('click', () => {
    document.querySelector('.review-details-container').scrollIntoView({ behavior: 'smooth' });
  });

  // Stats Dashboard: Clear Stats
  document.getElementById('clear-stats-btn').addEventListener('click', () => {
    if (confirm('คุณต้องการลบสถิติการสอบและประวัติทั้งหมดใช่หรือไม่? (ไม่สามารถกู้คืนได้)')) {
      clearStats();
    }
  });
}

// Confirm Exit to Home
function confirmExitToHome() {
  const currentScreen = Object.keys(screens).find(key => screens[key].classList.contains('active'));
  if (currentScreen === 'exam') {
    if (confirm('การทำแบบทดสอบยังไม่เสร็จสิ้น คุณต้องการยกเลิกและกลับหน้าหลักใช่หรือไม่? (สถิติรอบนี้จะไม่ถูกบันทึก)')) {
      clearInterval(examTimerInterval);
      switchScreen('home');
    }
  } else {
    switchScreen('home');
  }
}

// Switch Screens helper
function switchScreen(targetScreenName) {
  Object.keys(screens).forEach(key => {
    if (key === targetScreenName) {
      screens[key].classList.add('active');
    } else {
      screens[key].classList.remove('active');
    }
  });
  
  if (targetScreenName === 'home') {
    renderStats();
  }
}

// 5. Start Exam Session
function startExamSession(questionCount, isRealExam) {
  if (masterQuestions.length === 0) {
    alert('ขออภัย คลังข้อสอบยังไม่มีคำถาม กรุณาวางไฟล์ PDF หรือไฟล์คำถามก่อนครับ');
    return;
  }

  isRealExamMode = isRealExam;
  currentQuestionIndex = 0;
  
  // Sample questions randomly
  const shuffled = [...masterQuestions].sort(() => 0.5 - Math.random());
  activeQuestions = shuffled.slice(0, Math.min(questionCount, masterQuestions.length));
  
  // Reset session arrays
  userAnswers = new Array(activeQuestions.length).fill(null);
  flaggedQuestions = new Array(activeQuestions.length).fill(false);
  answeredOptionsLocked = new Array(activeQuestions.length).fill(false);
  
  // Set up timer / stats
  const timerBox = document.getElementById('timer-box');
  if (isRealExamMode) {
    document.getElementById('exam-mode-indicator').textContent = 'Real Exam Simulation';
    document.getElementById('exam-mode-indicator').style.backgroundColor = 'var(--accent-glow)';
    document.getElementById('exam-mode-indicator').style.color = 'var(--accent)';
    
    // 150 minutes for real exam
    examTimeTotal = 150 * 60;
    examTimeRemaining = examTimeTotal;
    examTimeSpent = 0;
    timerBox.classList.remove('hidden');
    startTimer();
  } else {
    document.getElementById('exam-mode-indicator').textContent = `Practice Mode (${activeQuestions.length} ข้อ)`;
    document.getElementById('exam-mode-indicator').style.backgroundColor = 'var(--bg-tertiary)';
    document.getElementById('exam-mode-indicator').style.color = 'var(--text-secondary)';
    
    // No strict countdown timer for practice mode, just count up to track time spent
    examTimeTotal = 0;
    examTimeRemaining = 0;
    examTimeSpent = 0;
    timerBox.classList.remove('hidden');
    startTimerCountUp();
  }
  
  // Show Screen
  switchScreen('exam');
  
  // Render layout
  renderQuestionNavGrid();
  showQuestion(0);
}

// Timer Functions
function startTimer() {
  clearInterval(examTimerInterval);
  updateTimerDisplay();
  
  examTimerInterval = setInterval(() => {
    examTimeRemaining--;
    examTimeSpent++;
    updateTimerDisplay();
    
    if (examTimeRemaining <= 0) {
      clearInterval(examTimerInterval);
      alert('หมดเวลาการสอบระบบจะทำการส่งข้อสอบของคุณโดยอัตโนมัติ');
      submitExam();
    }
  }, 1000);
}

function startTimerCountUp() {
  clearInterval(examTimerInterval);
  updateCountUpTimerDisplay();
  
  examTimerInterval = setInterval(() => {
    examTimeSpent++;
    updateCountUpTimerDisplay();
  }, 1000);
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function updateTimerDisplay() {
  document.getElementById('exam-timer').textContent = formatTime(examTimeRemaining);
}

function updateCountUpTimerDisplay() {
  document.getElementById('exam-timer').textContent = formatTime(examTimeSpent);
}

// 6. Show Question
function showQuestion(index) {
  currentQuestionIndex = index;
  const q = activeQuestions[index];
  
  // Update counters and progress bar
  document.getElementById('current-question-num').textContent = index + 1;
  document.getElementById('exam-progress-text').textContent = `${index + 1}/${activeQuestions.length}`;
  
  const answeredCount = userAnswers.filter(ans => ans !== null).length;
  document.getElementById('answered-count-text').textContent = `ตอบแล้ว: ${answeredCount} ข้อ`;
  
  const progressPercent = ((index + 1) / activeQuestions.length) * 100;
  document.getElementById('exam-progress-bar').style.width = `${progressPercent}%`;
  
  // Render texts
  document.getElementById('question-text-en').textContent = q.question_en;
  document.getElementById('question-text-th').textContent = q.question_th;
  
  // Render Options
  const optionsContainer = document.getElementById('options-container');
  optionsContainer.innerHTML = '';
  
  const prefix = ['A', 'B', 'C', 'D'];
  const optionsEn = q.options_en;
  const optionsTh = q.options_th;
  
  for (let i = 0; i < optionsEn.length; i++) {
    const btn = document.createElement('button');
    btn.className = 'option-btn';
    if (userAnswers[index] === i) {
      btn.classList.add('selected');
    }
    
    // For practice mode, show correct/incorrect state immediately if already locked
    if (!isRealExamMode && answeredOptionsLocked[index]) {
      if (i === q.answer_index) {
        btn.classList.add('correct');
      } else if (userAnswers[index] === i) {
        btn.classList.add('incorrect');
      }
    }
    
    btn.innerHTML = `
      <div class="option-prefix">${prefix[i]}</div>
      <div class="option-content">
        <span class="option-en" lang="en">${optionsEn[i]}</span>
        <span class="option-th" lang="th">${optionsTh[i]}</span>
      </div>
    `;
    
    btn.addEventListener('click', () => handleOptionClick(i));
    optionsContainer.appendChild(btn);
  }
  
  // Flag button state
  const flagBtn = document.getElementById('flag-question-btn');
  if (flaggedQuestions[index]) {
    flagBtn.classList.add('flagged-active');
    flagBtn.querySelector('.flag-text').textContent = 'ปักธงแล้ว';
  } else {
    btnRemoveClass(flagBtn, 'flagged-active');
    flagBtn.querySelector('.flag-text').textContent = 'ปักธงไว้ทบทวน';
  }
  
  // Explanation Visibility (Practice Mode only)
  const explanationContainer = document.getElementById('explanation-container');
  if (!isRealExamMode && answeredOptionsLocked[index]) {
    document.getElementById('explanation-text-en').textContent = q.explanation_en;
    document.getElementById('explanation-text-th').textContent = q.explanation_th;
    explanationContainer.classList.remove('hidden');
  } else {
    explanationContainer.classList.add('hidden');
  }
  
  // Navigation grid active update
  updateQuestionNavGridStates();
  
  // Update Prev / Next button status
  document.getElementById('prev-question-btn').disabled = (index === 0);
  document.getElementById('next-question-btn').disabled = (index === activeQuestions.length - 1);
  
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// Helper: remove class safely
function btnRemoveClass(btn, className) {
  if (btn) btn.classList.remove(className);
}

// Handle Option Clicks
function handleOptionClick(optionIndex) {
  const index = currentQuestionIndex;
  
  if (!isRealExamMode && answeredOptionsLocked[index]) {
    // Practice mode options are locked once selected
    return;
  }
  
  // Save answer
  userAnswers[index] = optionIndex;
  
  if (isRealExamMode) {
    // Real exam mode: just select and allow changing
    const buttons = document.querySelectorAll('#options-container .option-btn');
    buttons.forEach((btn, idx) => {
      if (idx === optionIndex) {
        btn.classList.add('selected');
      } else {
        btn.classList.remove('selected');
      }
    });
  } else {
    // Practice mode: lock answers and show explanation
    answeredOptionsLocked[index] = true;
    const q = activeQuestions[index];
    const buttons = document.querySelectorAll('#options-container .option-btn');
    
    buttons.forEach((btn, idx) => {
      if (idx === q.answer_index) {
        btn.classList.add('correct');
      } else if (idx === optionIndex) {
        btn.classList.add('incorrect');
      }
    });
    
    // Display explanation
    const explanationContainer = document.getElementById('explanation-container');
    document.getElementById('explanation-text-en').textContent = q.explanation_en;
    document.getElementById('explanation-text-th').textContent = q.explanation_th;
    explanationContainer.classList.remove('hidden');
    
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }
  
  // Update stats on header & nav bar
  const answeredCount = userAnswers.filter(ans => ans !== null).length;
  document.getElementById('answered-count-text').textContent = `ตอบแล้ว: ${answeredCount} ข้อ`;
  updateQuestionNavGridStates();
}

// Question Grid Generation
function renderQuestionNavGrid() {
  const gridContainer = document.getElementById('question-nav-grid');
  gridContainer.innerHTML = '';
  
  activeQuestions.forEach((_, idx) => {
    const item = document.createElement('div');
    item.className = 'nav-grid-item';
    item.textContent = idx + 1;
    item.id = `nav-grid-item-${idx}`;
    item.addEventListener('click', () => showQuestion(idx));
    gridContainer.appendChild(item);
  });
  
  updateQuestionNavGridStates();
}

function updateQuestionNavGridStates() {
  activeQuestions.forEach((_, idx) => {
    const item = document.getElementById(`nav-grid-item-${idx}`);
    if (!item) return;
    
    // Reset classes
    item.className = 'nav-grid-item';
    
    if (idx === currentQuestionIndex) {
      item.classList.add('current');
    }
    
    if (userAnswers[idx] !== null) {
      item.classList.add('answered');
    }
    
    if (flaggedQuestions[idx]) {
      item.classList.add('flagged');
    }
  });
}

// Next / Prev functions
function showPreviousQuestion() {
  if (currentQuestionIndex > 0) {
    showQuestion(currentQuestionIndex - 1);
  }
}

function showNextQuestion() {
  if (currentQuestionIndex < activeQuestions.length - 1) {
    showQuestion(currentQuestionIndex + 1);
  }
}

// Flag Question
function toggleFlagCurrentQuestion() {
  const idx = currentQuestionIndex;
  flaggedQuestions[idx] = !flaggedQuestions[idx];
  
  const flagBtn = document.getElementById('flag-question-btn');
  if (flaggedQuestions[idx]) {
    flagBtn.classList.add('flagged-active');
    flagBtn.querySelector('.flag-text').textContent = 'ปักธงแล้ว';
  } else {
    flagBtn.classList.remove('flagged-active');
    flagBtn.querySelector('.flag-text').textContent = 'ปักธงไว้ทบทวน';
  }
  
  updateQuestionNavGridStates();
}

// 7. Submit Exam and Generate Score
function submitExam() {
  clearInterval(examTimerInterval);
  
  let score = 0;
  activeQuestions.forEach((q, idx) => {
    if (userAnswers[idx] === q.answer_index) {
      score++;
    }
  });
  
  const percent = Math.round((score / activeQuestions.length) * 100);
  const isPass = percent >= 75; // CIA standard pass score estimate is 75%
  
  // Show score on review screen
  document.getElementById('result-score').textContent = `${score} / ${activeQuestions.length}`;
  document.getElementById('result-percentage').textContent = `${percent}%`;
  document.getElementById('result-time-spent').textContent = formatTime(examTimeSpent);
  
  const badge = document.getElementById('result-status-badge');
  if (isPass) {
    badge.textContent = 'PASS (ผ่าน)';
    badge.className = 'result-badge pass';
  } else {
    badge.textContent = 'FAIL (ไม่ผ่าน)';
    badge.className = 'result-badge fail';
  }
  
  document.getElementById('review-exam-mode').textContent = isRealExamMode 
    ? `จำลองข้อสอบจริง (Real Exam Simulation - ${activeQuestions.length} ข้อ)` 
    : `ฝึกฝนด่วน (Practice Mode - ${activeQuestions.length} ข้อ)`;
  
  // Save to statistics
  saveExamResult(activeQuestions.length, score, percent, isPass, isRealExamMode);
  
  // Render review explanations
  renderReviewDetails();
  
  // Switch Screen
  switchScreen('review');
  
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// Render Review Details list
function renderReviewDetails() {
  const container = document.getElementById('review-questions-list');
  container.innerHTML = '';
  
  activeQuestions.forEach((q, idx) => {
    const isCorrect = userAnswers[idx] === q.answer_index;
    const reviewItem = document.createElement('div');
    reviewItem.className = 'review-item card';
    
    let statusHTML = isCorrect
      ? `<span class="review-question-status status-correct"><i data-lucide="check-circle2"></i> ถูกต้อง (Correct)</span>`
      : `<span class="review-question-status status-incorrect"><i data-lucide="x-circle"></i> ผิด (Incorrect)</span>`;
      
    if (userAnswers[idx] === null) {
      statusHTML = `<span class="review-question-status status-incorrect"><i data-lucide="alert-circle"></i> ไม่ได้ทำ (Unanswered)</span>`;
    }
    
    let optionsHTML = '';
    const prefix = ['A', 'B', 'C', 'D'];
    
    q.options_en.forEach((optEn, optIdx) => {
      const optTh = q.options_th[optIdx];
      let optClass = 'review-option';
      
      // User selected this and it was correct
      if (userAnswers[idx] === optIdx && optIdx === q.answer_index) {
        optClass += ' user-correct';
      }
      // User selected this and it was incorrect
      else if (userAnswers[idx] === optIdx && optIdx !== q.answer_index) {
        optClass += ' user-incorrect';
      }
      // This is the correct answer (not selected by user)
      else if (optIdx === q.answer_index) {
        optClass += ' correct-answer';
      }
      
      optionsHTML += `
        <div class="${optClass}">
          <strong>${prefix[optIdx]}:</strong> 
          <div lang="en">${optEn}</div>
          <div lang="th">${optTh}</div>
        </div>
      `;
    });
    
    reviewItem.innerHTML = `
      <div class="review-question-header">
        <span class="review-question-num">ข้อที่ ${idx + 1}</span>
        ${statusHTML}
      </div>
      <div class="question-text-wrapper" style="margin-bottom: 15px;">
        <p class="question-en" lang="en"><strong>Q:</strong> ${q.question_en}</p>
        <p class="question-th" lang="th"><strong>คำถาม:</strong> ${q.question_th}</p>
      </div>
      <div class="review-options">
        ${optionsHTML}
      </div>
      <div class="explanation-box card" style="margin-top: 15px; border-color: rgba(99,102,241,0.2); background-color: rgba(99,102,241,0.01);">
        <div class="explanation-title" style="color: var(--primary);">
          <i data-lucide="info"></i>
          <span>คำอธิบาย / Explanation</span>
        </div>
        <div class="explanation-content">
          <p class="explanation-en" lang="en">${q.explanation_en}</p>
          <p class="explanation-th" lang="th">${q.explanation_th}</p>
        </div>
      </div>
    `;
    
    container.appendChild(reviewItem);
  });
}

// 8. Statistics and History Functions
function getHistory() {
  return JSON.parse(localStorage.getItem('cia-exam-history') || '[]');
}

function saveExamResult(totalQuestions, score, percent, isPass, isRealExam) {
  const history = getHistory();
  const newResult = {
    id: Date.now(),
    date: new Date().toLocaleDateString('th-TH', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }),
    totalQuestions,
    score,
    percent,
    isPass,
    isRealExam,
    part: currentPart
  };
  
  history.unshift(newResult); // Prepend to history list
  localStorage.setItem('cia-exam-history', JSON.stringify(history));
}

function clearStats() {
  localStorage.removeItem('cia-exam-history');
  renderStats();
}

function renderStats() {
  const history = getHistory();
  
  // Overall scores calculations
  const totalExams = history.length;
  document.getElementById('stats-total-exams').textContent = totalExams;
  
  if (totalExams === 0) {
    document.getElementById('stats-avg-score').textContent = '0%';
    document.getElementById('stats-pass-rate').textContent = '0%';
    
    // Clear list
    document.getElementById('stats-history-list').innerHTML = `
      <div class="empty-history">
        <i data-lucide="clipboard-list"></i>
        <p>ยังไม่มีประวัติการทำข้อสอบ เริ่มทำข้อสอบเพื่อเก็บสถิติกันเลย!</p>
      </div>
    `;
    if (window.lucide) window.lucide.createIcons();
    return;
  }
  
  const totalPercent = history.reduce((sum, item) => sum + item.percent, 0);
  const avgPercent = Math.round(totalPercent / totalExams);
  document.getElementById('stats-avg-score').textContent = `${avgPercent}%`;
  
  const passCount = history.filter(item => item.isPass).length;
  const passRate = Math.round((passCount / totalExams) * 100);
  document.getElementById('stats-pass-rate').textContent = `${passRate}%`;
  
  // Render history items list
  const historyList = document.getElementById('stats-history-list');
  historyList.innerHTML = '';
  
  history.slice(0, 10).forEach(item => { // Show last 10 entries
    const historyEl = document.createElement('div');
    historyEl.className = 'history-item';
    
    const badgeHTML = item.isPass 
      ? `<span class="badge-pass">PASS</span>` 
      : `<span class="badge-fail">FAIL</span>`;
      
    const modeLabel = item.isRealExam ? 'สอบจริง' : 'ฝึกฝน';
    const partLabel = item.part ? ` Part ${item.part}` : '';
    
    historyEl.innerHTML = `
      <div class="history-meta">
        <span class="history-title">${modeLabel}${partLabel} (${item.totalQuestions} ข้อ)</span>
        <span class="history-date">${item.date}</span>
      </div>
      <div class="history-result">
        <span class="history-score">${item.score}/${item.totalQuestions} (${item.percent}%)</span>
        ${badgeHTML}
      </div>
    `;
    historyList.appendChild(historyEl);
  });
  
  if (window.lucide) {
    window.lucide.createIcons();
  }
}
