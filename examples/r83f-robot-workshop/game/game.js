// level.js from original local model
// level.js
// Plain browser JavaScript, classic script. No imports/exports.
// All functions are attached to the global scope.

// --- parseLevel ---
// Parses a level string into the required 'level' object structure.
// Handles walls '#', floor '.', robot 'R', closed door 'D', open door 'd', terminal 'T'.
// Creates a doors object for both 'D' and 'd' tiles.
function parseLevel(text) {
    const lines = text.split('\n');
    const height = lines.length;
    if (height === 0) return null;
    
    const width = Math.max(...lines.map(line => line.length));
    const grid = [];
    const doors = {};
    let robot = { x: -1, y: -1 };

    for (let y = 0; y < height; y++) {
        const line = lines[y];
        const row = [];
        for (let x = 0; x < width; x++) {
            const char = line[x] || ' '; // Treat missing chars as empty space (wall effectively)
            row.push(char);

            if (char === 'R') {
                robot = { x, y };
            } else if (char === 'D' || char === 'd') {
                const key = `${x},${y}`;
                doors[key] = char === 'D' ? 'closed' : 'open';
            }
        }
        grid.push(row);
    }

    return {
        width,
        height,
        grid,
        robot,
        doors
    };
}

// --- isPassable ---
// Checks if a tile at (x, y) is passable given the level and current door states.
// Passable: '.', 'R', or a door ('D'/'d') that is currently 'open'.
// Not passable: '#', 'T', or a closed door.
function isPassable(level, doors, x, y) {
    if (x < 0 || x >= level.width || y < 0 || y >= level.height) {
        return false;
    }

    const tile = level.grid[y][x];

    // Check if it's a door
    if (tile === 'D' || tile === 'd') {
        const key = `${x},${y}`;
        // Doors are passable only if they are open
        return doors[key] === 'open';
    }

    // Check for standard passable tiles
    if (tile === '.' || tile === 'R') {
        return true;
    }

    // Everything else (walls '#', terminals 'T', empty spaces) is not passable
    return false;
}

// --- findPath ---
// Finds the shortest path from 'from' to 'to' using BFS.
// Returns an array of {x, y} objects representing the path steps.
// The path excludes the start node ('from') but includes the end node ('to').
// Returns [] if unreachable or if 'to' is not passable.
function findPath(level, doors, from, to) {
    const startX = from.x;
    const startY = from.y;
    const targetX = to.x;
    const targetY = to.y;

    // Validate start and target coordinates
    if (startX < 0 || startX >= level.width || startY < 0 || startY >= level.height) {
        return [];
    }
    if (targetX < 0 || targetX >= level.width || targetY < 0 || targetY >= level.height) {
        return [];
    }

    // Check if target is passable
    if (!isPassable(level, doors, targetX, targetY)) {
        return [];
    }

    // BFS Initialization
    // Queue stores {x, y, path: [{x,y}, ...]}
    // We store the path in the queue to reconstruct it easily.
    const queue = [];
    queue.push({ x: startX, y: startY, path: [] });

    // Visited set to prevent cycles and redundant processing.
    // We mark a tile as visited when we enqueue it.
    const visited = new Set();
    visited.add(`${startX},${startY}`);

    const directions = [
        { dx: 0, dy: -1 }, // Up
        { dx: 0, dy: 1 },  // Down
        { dx: -1, dy: 0 }, // Left
        { dx: 1, dy: 0 }   // Right
    ];

    while (queue.length > 0) {
        const current = queue.shift();
        const { x, y, path } = current;

        // If we reached the target
        if (x === targetX && y === targetY) {
            return path;
        }

        // Explore neighbors
        for (const dir of directions) {
            const nx = x + dir.dx;
            const ny = y + dir.dy;

            // Check bounds
            if (nx < 0 || nx >= level.width || ny < 0 || ny >= level.height) {
                continue;
            }

            // Check if passable
            if (!isPassable(level, doors, nx, ny)) {
                continue;
            }

            // Check if already visited
            const key = `${nx},${ny}`;
            if (visited.has(key)) {
                continue;
            }

            // Mark as visited and enqueue
            visited.add(key);
            const newPath = [...path, { x: nx, y: ny }];
            queue.push({ x: nx, y: ny, path: newPath });
        }
    }

    // Target not reachable
    return [];
}

// state.js from original local model
/*
 * state.js
 * Implements the game state logic for the robot pathfinding game.
 * Relies on global functions from level.js: parseLevel, isPassable, findPath.
 */

// --- Implementation ---

function createGame(text) {
    // Parse the raw text string into the level object
    const level = parseLevel(text);

    // Initialize game state
    // Deep copy robot position
    const game = {
        level: level,
        robot: { x: level.robot.x, y: level.robot.y },
        path: [],
        doors: {}, // Will be populated below
        dialog: null,
        paused: false
    };

    // Deep copy doors from level to game
    // level.doors is an object like {"0,0": "closed", "1,2": "open"}
    for (const key in level.doors) {
        game.doors[key] = level.doors[key];
    }

    return game;
}

function clickTile(game, x, y) {
    const level = game.level;
    const doors = game.doors;
    const robot = game.robot;
    const path = game.path;
    const dialog = game.dialog;

    // 1. Check if clicked tile is a door ('D' or 'd')
    // Note: The grid might contain 'D' or 'd', but we also track doors in the doors object.
    // We need to check if this coordinate corresponds to a door in our state.
    const doorKey = `${x},${y}`;
    const isDoorInState = doors.hasOwnProperty(doorKey);
    const isDoorChar = (level.grid[y] && level.grid[y][x] === 'D' || level.grid[y][x] === 'd');

    if (isDoorInState || isDoorChar) {
        // Check adjacency to robot (Manhattan distance == 1)
        const dist = Math.abs(robot.x - x) + Math.abs(robot.y - y);
        if (dist === 1) {
            // Toggle door state
            if (doors[doorKey] === 'open') {
                doors[doorKey] = 'closed';
            } else {
                doors[doorKey] = 'open';
            }
            // Clear path and dialog when interacting with a door
            path.length = 0;
            game.dialog = null;
            return;
        }
    }

    // 2. Check if clicked tile is a terminal 'T'
    if (level.grid[y] && level.grid[y][x] === 'T') {
        // Check adjacency to robot
        const dist = Math.abs(robot.x - x) + Math.abs(robot.y - y);
        if (dist === 1) {
            game.dialog = `TERMINAL ${x},${y}`;
            path.length = 0; // Clear path if terminal is clicked
            return;
        }
    }

    // 3. Check if clicked tile is passable
    // Use GLOBAL isPassable(level, doors, x, y)
    if (isPassable(level, doors, x, y)) {
        // Calculate shortest path
        const newPath = findPath(level, doors, robot, { x, y });
        path.length = 0;
        if (newPath.length > 0) {
            path.push(...newPath);
        }
        // Clear dialog if clicking a passable tile (unless it's a terminal handled above, 
        // but the prompt says "Clicking any passable tile clears the dialog")
        game.dialog = null;
    } else {
        // Clicked wall or non-passable tile -> do nothing
        // However, if it was a door but not adjacent, we already handled it (did nothing).
        // If it was a terminal but not adjacent, we already handled it (did nothing).
    }
}

function stepGame(game, n) {
    const path = game.path;
    const robot = game.robot;

    // Robot advances exactly one tile of its path per step.
    // stepGame(game, n) moves up to n steps.
    // Since the prompt says "advances exactly one tile... per step", 
    // and stepGame takes n, we assume n is the number of steps to take.
    
    for (let i = 0; i < n; i++) {
        if (path.length === 0) break;

        const nextTile = path[0];
        
        // Move robot
        robot.x = nextTile.x;
        robot.y = nextTile.y;

        // Remove the tile we just walked on from the path
        path.shift();
    }
}

function saveGame(game) {
    const saveData = {
        robot: game.robot,
        doors: game.doors
    };
    localStorage.setItem("af-robot-save", JSON.stringify(saveData));
}

function loadGame(game) {
    const saved = localStorage.getItem("af-robot-save");
    if (saved) {
        try {
            const data = JSON.parse(saved);
            // Restore robot position
            game.robot = { x: data.robot.x, y: data.robot.y };
            // Restore doors
            game.doors = {};
            for (const key in data.doors) {
                game.doors[key] = data.doors[key];
            }
            // Clear path and dialog as per spec
            game.path = [];
            game.dialog = null;
        } catch (e) {
            console.error("Failed to load game state:", e);
        }
    }
}

// render.js from original local model
function drawGame(game, canvas) {
    // Set canvas dimensions based on level size
    canvas.width = game.level.width * 32;
    canvas.height = game.level.height * 32;
    
    const ctx = canvas.getContext('2d');
    
    // Helper to get door color based on state
    function getDoorColor(state) {
        if (state === 'closed') return 'rgb(139,69,19)';
        if (state === 'open') return 'rgb(222,184,135)';
        return null;
    }

    // Helper to get base tile color from grid character
    function getBaseColor(char) {
        switch (char) {
            case '#': return 'rgb(32,32,32)'; // wall
            case '.': return 'rgb(208,208,208)'; // floor
            case 'T': return 'rgb(30,90,200)'; // terminal
            default: return 'rgb(208,208,208)'; // default to floor
        }
    }

    // Render the grid
    for (let y = 0; y < game.level.height; y++) {
        for (let x = 0; x < game.level.width; x++) {
            const key = x + ',' + y;
            const char = game.level.grid[y][x];
            
            // Check for door override first (Priority Rule)
            if (Object.prototype.hasOwnProperty.call(game.doors, key)) {
                const doorState = game.doors[key];
                ctx.fillStyle = getDoorColor(doorState);
                ctx.fillRect(x * 32, y * 32, 32, 32);
            } else {
                // No door key, use grid character
                ctx.fillStyle = getBaseColor(char);
                ctx.fillRect(x * 32, y * 32, 32, 32);
            }
        }
    }

    // Render Robot
    const r = game.robot;
    const robotX = r.x * 32;
    const robotY = r.y * 32;
    
    // Draw 20x20 square centered in the 32x32 tile
    // Center offset: (32 - 20) / 2 = 6
    ctx.fillStyle = 'rgb(220,40,40)';
    ctx.fillRect(robotX + 6, robotY + 6, 20, 20);
}

// main.js from original R83E local model response
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

