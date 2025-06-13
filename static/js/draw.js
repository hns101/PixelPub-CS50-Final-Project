document.addEventListener('DOMContentLoaded', () => {
    // Connect to the WebSocket server
    const socket = io();

    const canvas = document.getElementById('pixel-canvas');
    const ctx = canvas.getContext('2d');

    // --- Configuration from HTML data attributes ---
    const PIXEL_SIZE = 20;
    const CANVAS_ID = canvas.dataset.canvasId;
    const GRID_WIDTH = parseInt(canvas.dataset.canvasWidth, 10);
    const GRID_HEIGHT = parseInt(canvas.dataset.canvasHeight, 10);
    const canvasWidth = PIXEL_SIZE * GRID_WIDTH;
    const canvasHeight = PIXEL_SIZE * GRID_HEIGHT;
    const GRID_COLOR = "#333";
    let canvasData = JSON.parse(canvas.dataset.canvasData);

    // --- State ---
    let selectedColor = '#FFFFFF'; // Default to white
    const colors = [
        '#FFFFFF', '#C1C1C1', '#EF130B', '#FF7100', '#FFE400', '#00CC00',
        '#00B2FF', '#231FD3', '#A300BA', '#634b35', '#000000', '#ff99aa'
    ];

    // --- WebSocket Event Handlers ---
    socket.on('connect', () => {
        console.log('Connected to server!');
        // Join the room for this specific canvas
        socket.emit('join_canvas', { canvas_id: CANVAS_ID });
    });

    // Listen for pixels placed by OTHER users
    socket.on('pixel_placed', (data) => {
        console.log('Received pixel from another user:', data);
        // Update local data and redraw that pixel
        canvasData[data.y][data.x] = data.color;
        fillPixel(data.x, data.y, data.color);
    });

    // --- Initialization ---
    function initialize() {
        canvas.width = canvasWidth;
        canvas.height = canvasHeight;
        setupPalette();
        drawFullCanvas(); // Draw the initial state
        drawGrid();
        canvas.addEventListener('click', handleCanvasClick);
    }

    // --- UI Setup ---
    function setupPalette() {
        const paletteContainer = document.getElementById('color-palette');
        paletteContainer.innerHTML = '';
        colors.forEach(color => {
            const colorDiv = document.createElement('div');
            colorDiv.style.backgroundColor = color;
            colorDiv.style.width = '40px';
            colorDiv.style.height = '40px';
            colorDiv.style.margin = '5px';
            colorDiv.style.cursor = 'pointer';
            colorDiv.style.border = '2px solid transparent';
            colorDiv.addEventListener('click', () => {
                selectedColor = color;
                document.querySelectorAll('#color-palette div').forEach(div => {
                    div.style.border = '2px solid transparent';
                });
                colorDiv.style.border = '2px solid #00B2FF';
            });
            paletteContainer.appendChild(colorDiv);
        });
        paletteContainer.firstChild.style.border = '2px solid #00B2FF';
    }

    // --- Drawing Functions ---
    function drawGrid() {
        ctx.strokeStyle = GRID_COLOR;
        ctx.lineWidth = 1;
        for (let x = 0; x <= canvasWidth; x += PIXEL_SIZE) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvasHeight); ctx.stroke();
        }
        for (let y = 0; y <= canvasHeight; y += PIXEL_SIZE) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvasWidth, y); ctx.stroke();
        }
    }
    
    // Draws a single pixel
    function fillPixel(x, y, color) {
        ctx.fillStyle = color;
        ctx.fillRect(x * PIXEL_SIZE, y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE);
    }
    
    // Redraws the entire canvas from the canvasData array
    function drawFullCanvas() {
        for (let y = 0; y < GRID_HEIGHT; y++) {
            for (let x = 0; x < GRID_WIDTH; x++) {
                fillPixel(x, y, canvasData[y][x]);
            }
        }
        drawGrid();
    }

    // --- Event Handlers ---
    function handleCanvasClick(event) {
        const rect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;
        const gridX = Math.floor(mouseX / PIXEL_SIZE);
        const gridY = Math.floor(mouseY / PIXEL_SIZE);

        // Instantly draw the pixel for the current user for better responsiveness
        fillPixel(gridX, gridY, selectedColor);
        // And update local data model
        canvasData[gridY][gridX] = selectedColor;

        // Then, send the pixel data to the server
        socket.emit('place_pixel', {
            canvas_id: CANVAS_ID,
            x: gridX,
            y: gridY,
            color: selectedColor
        });
    }

    // --- Start the app ---
    initialize();
});