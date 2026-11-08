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
