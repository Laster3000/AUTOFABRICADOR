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
