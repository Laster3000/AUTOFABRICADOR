let GAME = createGame(window.AF_DEFAULT_LEVEL);
const canvas = document.getElementById('game');
const dialog = document.getElementById('dialog');
const saveBtn = document.getElementById('save');
const loadBtn = document.getElementById('load');

canvas.width = GAME.level.width * 32;
canvas.height = GAME.level.height * 32;
drawGame(GAME, canvas);

canvas.addEventListener('click', e => {
  const x = Math.floor(e.offsetX / 32);
  const y = Math.floor(e.offsetY / 32);
  clickTile(GAME, x, y);
  dialog.textContent = GAME.dialog || '';
  drawGame(GAME, canvas);
});

saveBtn.addEventListener('click', () => {
  saveGame(GAME);
  dialog.textContent = GAME.dialog || '';
  drawGame(GAME, canvas);
});

loadBtn.addEventListener('click', () => {
  loadGame(GAME);
  dialog.textContent = GAME.dialog || '';
  drawGame(GAME, canvas);
});

setInterval(() => {
  if (!GAME.paused && GAME.path.length > 0) {
    stepGame(GAME, 1);
    drawGame(GAME, canvas);
  }
}, 150);

window.AF_TEST = {
  loadLevel: (text) => {
    GAME = createGame(text);
    GAME.paused = false;
    GAME.dialog = null;
    dialog.textContent = '';
    drawGame(GAME, canvas);
  },
  state: () => ({
    robot: { x: GAME.robot.x, y: GAME.robot.y },
    path: GAME.path.map(p => [p.x, p.y]),
    doors: Object.assign({}, GAME.doors),
    dialog: GAME.dialog
  }),
  step: (n) => {
    stepGame(GAME, n);
    drawGame(GAME, canvas);
  },
  pause: (flag) => {
    GAME.paused = !!flag;
  }
};
