document.addEventListener('DOMContentLoaded', () => {
    // --- Setup & Config ---
    const socket = io();
    const canvas = document.getElementById('pixel-canvas');
    const colorPicker = document.getElementById('color-picker');
    const gridToggle = document.getElementById('grid-toggle');
    const zoomSlider = document.getElementById('zoom-slider'); // New slider element
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const ctx = canvas.getContext('2d');

    const PUB_ID = canvas.dataset.pubId;
    const CANVAS_ID = canvas.dataset.canvasId;
    const GRID_WIDTH = parseInt(canvas.dataset.canvasWidth, 10);
    const GRID_HEIGHT = parseInt(canvas.dataset.canvasHeight, 10);
    
    const GRID_COLOR = "#DDDDDD";
    let canvasData = JSON.parse(canvas.dataset.canvasData);

    // --- State Management ---
    let zoomLevel = 15; // Represents the size of each pixel.
    const MIN_ZOOM = 2;
    const MAX_ZOOM = 40;
    let selectedColor = colorPicker.value;
    let isDrawing = false;
    let lastDrawnPixel = { x: null, y: null };

    // --- WebSocket Handlers ---
    socket.on('connect', () => socket.emit('join_pub', { pub_id: PUB_ID }));
    socket.on('pixel_placed', (data) => {
        canvasData[data.y][data.x] = data.color;
        redrawCanvas();
    });
    socket.on('new_message', (data) => appendMessage(data));

    // --- Chat Functions ---
    function appendMessage(data) {
        const messageEl = document.createElement('div');
        messageEl.classList.add('chat-message', 'mb-2');
        messageEl.innerHTML = `<img src="/avatar/${data.avatar_id}.png" class="avatar-sm me-2"><div><strong class="me-2">${data.username}</strong><small class="text-muted">${new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</small><p class="mb-0">${data.content}</p></div>`;
        chatMessages.appendChild(messageEl);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // --- Drawing & Canvas Functions ---
    function updateCanvasSize() {
        canvas.width = GRID_WIDTH * zoomLevel;
        canvas.height = GRID_HEIGHT * zoomLevel;
        redrawCanvas();
    }

    function drawGrid() {
        ctx.strokeStyle = GRID_COLOR;
        ctx.lineWidth = 1;
        for (let x = 0; x <= canvas.width; x += zoomLevel) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke(); }
        for (let y = 0; y <= canvas.height; y += zoomLevel) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke(); }
    }
    
    function redrawCanvas() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        for (let y = 0; y < GRID_HEIGHT; y++) {
            for (let x = 0; x < GRID_WIDTH; x++) {
                ctx.fillStyle = canvasData[y][x];
                ctx.fillRect(x * zoomLevel, y * zoomLevel, zoomLevel, zoomLevel);
            }
        }
        if (gridToggle.checked) drawGrid();
    }
    
    function placePixel(gridX, gridY) {
        if (gridX < 0 || gridX >= GRID_WIDTH || gridY < 0 || gridY >= GRID_HEIGHT) return;
        if (lastDrawnPixel.x === gridX && lastDrawnPixel.y === gridY) return;
        
        canvasData[gridY][gridX] = selectedColor;
        redrawCanvas();
        socket.emit('place_pixel', { pub_id: PUB_ID, canvas_id: CANVAS_ID, x: gridX, y: gridY, color: selectedColor });
        lastDrawnPixel = { x: gridX, y: gridY };
    }
    
    // --- Event Listeners ---
    function initialize() {
        // Set initial slider and canvas size
        zoomSlider.min = MIN_ZOOM;
        zoomSlider.max = MAX_ZOOM;
        zoomSlider.value = zoomLevel;
        updateCanvasSize(); 
        
        chatMessages.scrollTop = chatMessages.scrollHeight;

        colorPicker.addEventListener('input', (e) => selectedColor = e.target.value);
        gridToggle.addEventListener('change', redrawCanvas);

        // Zoom slider listener
        zoomSlider.addEventListener('input', (e) => {
            zoomLevel = parseInt(e.target.value, 10);
            updateCanvasSize();
        });

        // Drawing listeners
        canvas.addEventListener('mousedown', (e) => {
            isDrawing = true;
            placePixel(getCoords(e).x, getCoords(e).y);
        });
        canvas.addEventListener('mousemove', (e) => { if (isDrawing) placePixel(getCoords(e).x, getCoords(e).y); });
        document.addEventListener('mouseup', () => {
            isDrawing = false;
            lastDrawnPixel = { x: null, y: null };
        });
        canvas.addEventListener('mouseleave', () => {
            isDrawing = false;
            lastDrawnPixel = { x: null, y: null };
        });

        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = chatInput.value.trim();
            if (message) {
                socket.emit('send_message', { pub_id: PUB_ID, content: message });
                chatInput.value = '';
            }
        });
    }

    // Calculates coordinates based on the current zoom level.
    function getCoords(event) {
        const rect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;
        return {
            x: Math.floor(mouseX / zoomLevel),
            y: Math.floor(mouseY / zoomLevel)
        };
    }
    
    initialize();
});