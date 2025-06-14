document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const canvas = document.getElementById('pixel-canvas');
    const tooltip = document.getElementById('tooltip');
    const ctx = canvas.getContext('2d');

    // --- Config from HTML ---
    const PIXEL_SIZE = 20;
    const CANVAS_ID = canvas.dataset.canvasId;
    const GRID_WIDTH = parseInt(canvas.dataset.canvasWidth, 10);
    const GRID_HEIGHT = parseInt(canvas.dataset.canvasHeight, 10);
    const IS_COMMUNITY = canvas.dataset.isCommunity === 'true';
    const canvasWidth = PIXEL_SIZE * GRID_WIDTH;
    const canvasHeight = PIXEL_SIZE * GRID_HEIGHT;
    const GRID_COLOR = "#333";
    let canvasData = JSON.parse(canvas.dataset.canvasData);

    // --- State ---
    let selectedColor = '#FFFFFF';
    let lastHoveredPixel = { x: -1, y: -1 };
    const colors = [
        '#FFFFFF', '#C1C1C1', '#EF130B', '#FF7100', '#FFE400', '#00CC00',
        '#00B2FF', '#231FD3', '#A300BA', '#634b35', '#000000', '#ff99aa'
    ];

    // --- WebSocket Event Handlers ---
    socket.on('connect', () => {
        socket.emit('join_canvas', { canvas_id: CANVAS_ID });
    });

    socket.on('pixel_placed', (data) => {
        canvasData[data.y][data.x] = data.color;
        fillPixel(data.x, data.y, data.color);
    });
    
    // NEW: Listen for history response
    socket.on('history_response', (data) => {
        if (data.username) {
            tooltip.innerHTML = `Last modified by: <strong>${data.username}</strong><br><small>${new Date(data.timestamp).toLocaleString()}</small>`;
            tooltip.style.display = 'block';
        }
    });

    // --- Initialization ---
    function initialize() {
        canvas.width = canvasWidth;
        canvas.height = canvasHeight;
        setupPalette();
        drawFullCanvas();
        canvas.addEventListener('click', handleCanvasClick);
        // NEW: Add hover and leave listeners
        if (IS_COMMUNITY) {
            canvas.addEventListener('mousemove', handleCanvasHover);
            canvas.addEventListener('mouseleave', () => {
                tooltip.style.display = 'none';
                lastHoveredPixel = { x: -1, y: -1 };
            });
        }
    }

    // --- UI Setup & Drawing (No changes needed here) ---
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
    function drawGrid() {
        ctx.strokeStyle = GRID_COLOR; ctx.lineWidth = 1;
        for (let x = 0; x <= canvasWidth; x += PIXEL_SIZE) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvasHeight); ctx.stroke(); }
        for (let y = 0; y <= canvasHeight; y += PIXEL_SIZE) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvasWidth, y); ctx.stroke(); }
    }
    function fillPixel(x, y, color) { ctx.fillStyle = color; ctx.fillRect(x * PIXEL_SIZE, y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE); }
    function drawFullCanvas() {
        for (let y = 0; y < GRID_HEIGHT; y++) {
            for (let x = 0; x < GRID_WIDTH; x++) { fillPixel(x, y, canvasData[y][x]); }
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

        fillPixel(gridX, gridY, selectedColor);
        canvasData[gridY][gridX] = selectedColor;

        socket.emit('place_pixel', { canvas_id: CANVAS_ID, x: gridX, y: gridY, color: selectedColor });
    }

    // NEW: Hover handler
    function handleCanvasHover(event) {
        const rect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;
        const gridX = Math.floor(mouseX / PIXEL_SIZE);
        const gridY = Math.floor(mouseY / PIXEL_SIZE);
        
        // Update tooltip position
        tooltip.style.left = `${event.pageX + 15}px`;
        tooltip.style.top = `${event.pageY + 15}px`;

        // If hovering over a new pixel, request its history
        if (gridX !== lastHoveredPixel.x || gridY !== lastHoveredPixel.y) {
            lastHoveredPixel = { x: gridX, y: gridY };
            tooltip.style.display = 'none'; // Hide until we get a response
            socket.emit('request_history', { canvas_id: CANVAS_ID, x: gridX, y: gridY });
        }
    }
    
    initialize();
});
