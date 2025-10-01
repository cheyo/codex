const STORAGE_KEY = 'habit-tasks';
const COLOR_PALETTE = ['--accent-1', '--accent-2', '--accent-3', '--accent-4', '--accent-5'];

const taskForm = document.querySelector('#task-form');
const taskNameInput = document.querySelector('#task-name');
const tasksContainer = document.querySelector('#tasks-container');
const taskTemplate = document.querySelector('#task-template');

let tasks = loadTasks();
const viewState = new Map();

function loadTasks() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return [];
    const parsed = JSON.parse(saved);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.error('加载任务失败', error);
    return [];
  }
}

function saveTasks() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
}

function createTask(name) {
  const colorIndex = tasks.length % COLOR_PALETTE.length;
  const id = typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `task-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return {
    id,
    name,
    color: COLOR_PALETTE[colorIndex],
    records: [],
  };
}

function formatDate(date) {
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
}

function renderTasks() {
  tasksContainer.innerHTML = '';

  if (!tasks.length) {
    const empty = document.createElement('p');
    empty.className = 'empty-tip';
    empty.textContent = '还没有任务，先添加一个打卡任务吧！';
    tasksContainer.appendChild(empty);
    return;
  }

  tasks.forEach((task, index) => {
    const node = taskTemplate.content.firstElementChild.cloneNode(true);
    const titleEl = node.querySelector('.task-card__title');
    const todayBtn = node.querySelector('.task-card__today');
    const deleteBtn = node.querySelector('.task-card__delete');
    const prevBtn = node.querySelector('.calendar__nav--prev');
    const nextBtn = node.querySelector('.calendar__nav--next');
    const labelEl = node.querySelector('.calendar__label');
    const gridEl = node.querySelector('.calendar__grid');

    titleEl.textContent = task.name;
    const color = getColorValue(task.color);
    node.style.setProperty('--task-color', color);

    const { year, month } = getViewMonth(task.id);
    renderCalendar(task, year, month, labelEl, gridEl);

    prevBtn.addEventListener('click', () => {
      const { year: currentYear, month: currentMonth } = getViewMonth(task.id);
      const prevDate = new Date(currentYear, currentMonth - 1, 1);
      setViewMonth(task.id, prevDate.getFullYear(), prevDate.getMonth());
      renderCalendar(task, prevDate.getFullYear(), prevDate.getMonth(), labelEl, gridEl);
    });

    nextBtn.addEventListener('click', () => {
      const { year: currentYear, month: currentMonth } = getViewMonth(task.id);
      const nextDate = new Date(currentYear, currentMonth + 1, 1);
      setViewMonth(task.id, nextDate.getFullYear(), nextDate.getMonth());
      renderCalendar(task, nextDate.getFullYear(), nextDate.getMonth(), labelEl, gridEl);
    });

    todayBtn.addEventListener('click', () => {
      toggleRecord(task, new Date());
      const { year: viewYear, month: viewMonth } = getViewMonth(task.id);
      renderCalendar(task, viewYear, viewMonth, labelEl, gridEl);
    });

    deleteBtn.addEventListener('click', () => {
      if (confirm(`确定删除任务「${task.name}」吗？`)) {
        tasks = tasks.filter((item) => item.id !== task.id);
        viewState.delete(task.id);
        saveTasks();
        renderTasks();
      }
    });

    tasksContainer.appendChild(node);
  });
}

function renderCalendar(task, year, month, labelEl, gridEl) {
  const displayDate = new Date(year, month, 1);
  const monthLabel = `${displayDate.getFullYear()}年${displayDate.getMonth() + 1}月`;
  labelEl.textContent = monthLabel;

  gridEl.innerHTML = '';

  const firstDay = new Date(year, month, 1);
  const startDay = firstDay.getDay(); // Sunday = 0
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const prevMonthDays = startDay; // number of days from previous month to fill first week
  const totalCells = Math.ceil((prevMonthDays + daysInMonth) / 7) * 7;

  for (let cellIndex = 0; cellIndex < totalCells; cellIndex++) {
    const cell = document.createElement('div');
    cell.className = 'calendar__cell';
    const content = document.createElement('div');
    content.className = 'calendar__cell-content';

    const dateOffset = cellIndex - prevMonthDays + 1;
    const cellDate = new Date(year, month, dateOffset);
    const isCurrentMonth = cellDate.getMonth() === month;

    if (!isCurrentMonth) {
      cell.classList.add('is-out-month');
    }

    if (isCurrentMonth && dateOffset > 0 && dateOffset <= daysInMonth) {
      content.textContent = dateOffset;
      cell.dataset.date = formatDate(cellDate);
      if (task.records.includes(cell.dataset.date)) {
        cell.classList.add('is-checked');
      }
      cell.addEventListener('click', () => {
        toggleRecord(task, cellDate);
        renderCalendar(task, year, month, labelEl, gridEl);
      });
    } else {
      content.textContent = cellDate.getDate();
    }

    cell.appendChild(content);
    gridEl.appendChild(cell);
  }
}

function toggleRecord(task, date) {
  const dateKey = formatDate(date);
  const hasRecord = task.records.includes(dateKey);

  if (hasRecord) {
    task.records = task.records.filter((item) => item !== dateKey);
  } else {
    task.records.push(dateKey);
    task.records.sort();
  }

  saveTasks();
}

function getColorValue(varName) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(varName);
  return value ? value.trim() : '#4a6cf7';
}

function getViewMonth(taskId) {
  if (!viewState.has(taskId)) {
    const now = new Date();
    viewState.set(taskId, { year: now.getFullYear(), month: now.getMonth() });
  }
  return viewState.get(taskId);
}

function setViewMonth(taskId, year, month) {
  viewState.set(taskId, { year, month });
}

function init() {
  taskForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const name = taskNameInput.value.trim();
    if (!name) return;

    const newTask = createTask(name);
    tasks.push(newTask);
    saveTasks();
    taskNameInput.value = '';
    renderTasks();
  });

  renderTasks();
}

init();
