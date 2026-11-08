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
