document.addEventListener('DOMContentLoaded', () => {
    // --- Setup & Config ---
    const socket = io();
    const canvas = document.getElementById('pixel-canvas');
    const tooltip = document.getElementById('tooltip');
    const colorPicker = document.getElementById('color-picker');
    const gridToggle = document.getElementById('grid-toggle');
    const ctx = canvas.getContext('2d');

    const PIXEL_SIZE = 20;
    const CANVAS_ID = canvas.dataset.canvasId;
    const GRID_WIDTH = parseInt(canvas.dataset.canvasWidth, 10);
    const GRID_HEIGHT = parseInt(canvas.dataset.canvasHeight, 10);
    const IS_COMMUNITY = canvas.dataset.isCommunity === 'true';
    const canvasWidth = PIXEL_SIZE * GRID_WIDTH;
    const canvasHeight = PIXEL_SIZE * GRID_HEIGHT;
    const GRID_COLOR = "#EEEEEE";
    let canvasData = JSON.parse(canvas.dataset.canvasData);

    // --- State Management ---
    let selectedColor = colorPicker.value;
    let isDrawing = false;
    let lastDrawnPixel = { x: null, y: null };
    let lastHoveredPixel = { x: -1, y: -1 };

    // --- WebSocket Handlers ---
    socket.on('connect', () => socket.emit('join_canvas', { canvas_id: CANVAS_ID }));
    socket.on('pixel_placed', (data) => {
        canvasData[data.y][data.x] = data.color;
        redrawCanvas();
    });
    socket.on('history_response', (data) => {
        if (data.username) {
            tooltip.innerHTML = `Last modified by: <strong>${data.username}</strong><br><small>${new Date(data.timestamp).toLocaleString()}</small>`;
            tooltip.style.display = 'block';
        }
    });

    // --- Main Drawing & Redrawing Functions ---
    function drawGrid() {
        ctx.strokeStyle = GRID_COLOR;
        ctx.lineWidth = 0.5;
        for (let x = 0; x <= canvasWidth; x += PIXEL_SIZE) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvasHeight); ctx.stroke();
        }
        for (let y = 0; y <= canvasHeight; y += PIXEL_SIZE) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvasWidth, y); ctx.stroke();
        }
    }

    function redrawCanvas() {
        // Clear the entire canvas
        ctx.clearRect(0, 0, canvasWidth, canvasHeight);
        
        // Draw all the pixels from our data model
        for (let y = 0; y < GRID_HEIGHT; y++) {
            for (let x = 0; x < GRID_WIDTH; x++) {
                ctx.fillStyle = canvasData[y][x];
                ctx.fillRect(x * PIXEL_SIZE, y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE);
            }
        }
        // If the toggle is checked, draw the grid on top
        if (gridToggle.checked) {
            drawGrid();
        }
    }

    // --- Event Logic ---
    function placePixel(gridX, gridY) {
        // Prevent drawing the same pixel repeatedly while dragging
        if (lastDrawnPixel.x === gridX && lastDrawnPixel.y === gridY) {
            return;
        }
        
        // Update local data model and redraw immediately for responsiveness
        canvasData[gridY][gridX] = selectedColor;
        redrawCanvas();
        
        // Send the pixel to the server
        socket.emit('place_pixel', {
            canvas_id: CANVAS_ID,
            x: gridX,
            y: gridY,
            color: selectedColor
        });

        lastDrawnPixel = { x: gridX, y: gridY };
    }

    // --- Event Listeners Setup ---
    function initialize() {
        canvas.width = canvasWidth;
        canvas.height = canvasHeight;
        redrawCanvas(); // Initial draw (will be solid white, no grid)

        // Color Picker
        colorPicker.addEventListener('input', (e) => {
            selectedColor = e.target.value;
        });

        // Grid Toggle
        gridToggle.addEventListener('change', redrawCanvas);

        // Drawing Listeners
        canvas.addEventListener('mousedown', (e) => {
            isDrawing = true;
            const coords = getCoords(e);
            placePixel(coords.x, coords.y);
        });

        canvas.addEventListener('mousemove', (e) => {
            if (isDrawing) {
                const coords = getCoords(e);
                placePixel(coords.x, coords.y);
            }
        });

        canvas.addEventListener('mouseup', () => {
            isDrawing = false;
            lastDrawnPixel = { x: null, y: null }; // Reset for next drag
        });

        canvas.addEventListener('mouseleave', () => {
            isDrawing = false;
            lastDrawnPixel = { x: null, y: null };
            tooltip.style.display = 'none';
        });
        
        // History Hover Listener
        if (IS_COMMUNITY) {
            canvas.addEventListener('mousemove', handleHistoryHover);
        }
    }

    // --- Helper Functions ---
    function getCoords(event) {
        const rect = canvas.getBoundingClientRect();
        return {
            x: Math.floor((event.clientX - rect.left) / PIXEL_SIZE),
            y: Math.floor((event.clientY - rect.top) / PIXEL_SIZE)
        };
    }
    
    function handleHistoryHover(event) {
        if (isDrawing) return; // Don't show tooltip while drawing
        
        const coords = getCoords(event);
        tooltip.style.left = `${event.pageX + 15}px`;
        tooltip.style.top = `${event.pageY + 15}px`;

        if (coords.x !== lastHoveredPixel.x || coords.y !== lastHoveredPixel.y) {
            lastHoveredPixel = coords;
            tooltip.style.display = 'none';
            socket.emit('request_history', { canvas_id: CANVAS_ID, x: coords.x, y: coords.y });
        }
    }

    // --- Start the app ---
    initialize();
});