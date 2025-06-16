document.addEventListener('DOMContentLoaded', () => {
    // --- Setup & Config ---
    const socket = io();
    const canvas = document.getElementById('pixel-canvas');
    const colorPicker = document.getElementById('color-picker');
    const gridToggle = document.getElementById('grid-toggle');
    const zoomSlider = document.getElementById('zoom-slider');
    const brushSlider = document.getElementById('brush-slider');
    const brushSizeDisplay = document.getElementById('brush-size-display');
    const downloadBtn = document.getElementById('download-btn'); // New element
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const pixelInfoDisplay = document.getElementById('pixel-info-display');
    const ctx = canvas.getContext('2d');

    const PUB_ID = canvas.dataset.pubId;
    const CANVAS_ID = canvas.dataset.canvasId;
    const GRID_WIDTH = parseInt(canvas.dataset.canvasWidth, 10);
    const GRID_HEIGHT = parseInt(canvas.dataset.canvasHeight, 10);
    
    const GRID_COLOR = "#DDDDDD";
    let canvasData = JSON.parse(canvas.dataset.canvasData);

    // --- State Management ---
    let zoomLevel = 15;
    let brushSize = 1;
    const MIN_ZOOM = 2;
    const MAX_ZOOM = 40;
    let selectedColor = colorPicker.value;
    let isDrawing = false;
    let lastHoveredPixel = { x: -1, y: -1 };
    let pixelsToLog = [];

    // --- WebSocket Handlers ---
    socket.on('connect', () => socket.emit('join_pub', { pub_id: PUB_ID }));
    socket.on('pixel_placed', (data) => {
        canvasData[data.y][data.x] = data.color;
        redrawCanvas();
    });
    socket.on('new_message', (data) => appendMessage(data));

    socket.on('history_response', (data) => {
        if (data.username) {
            pixelInfoDisplay.innerHTML = `(${lastHoveredPixel.x}, ${lastHoveredPixel.y}) by <strong>${data.username}</strong>`;
            pixelInfoDisplay.style.display = 'block';
        }
    });

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
    
    function applyBrush(centerX, centerY) {
        const radius = Math.floor((brushSize - 1) / 2);
        for (let y = centerY - radius; y <= centerY + radius; y++) {
            for (let x = centerX - radius; x <= centerX + radius; x++) {
                placePixel(x, y);
            }
        }
    }

    function placePixel(gridX, gridY) {
        if (gridX < 0 || gridX >= GRID_WIDTH || gridY < 0 || gridY >= GRID_HEIGHT) return;
        if (canvasData[gridY][gridX] === selectedColor) return;
        
        canvasData[gridY][gridX] = selectedColor;
        socket.emit('place_pixel', { pub_id: PUB_ID, canvas_id: CANVAS_ID, x: gridX, y: gridY, color: selectedColor });
        pixelsToLog.push({ x: gridX, y: gridY, color: selectedColor });
    }

    function saveAndLog() {
        if (pixelsToLog.length > 0) {
            socket.emit('log_pixel_history', { canvas_id: CANVAS_ID, pixels: pixelsToLog });
            pixelsToLog = [];
        }
        socket.emit('save_canvas_state', { canvas_id: CANVAS_ID, canvas_data: canvasData });
    }
    
    // --- Event Listeners ---
    function initialize() {
        zoomSlider.value = zoomLevel;
        brushSlider.value = brushSize;
        brushSizeDisplay.textContent = brushSize;
        updateCanvasSize(); 
        chatMessages.scrollTop = chatMessages.scrollHeight;

        colorPicker.addEventListener('input', (e) => selectedColor = e.target.value);
        gridToggle.addEventListener('change', redrawCanvas);
        zoomSlider.addEventListener('input', (e) => {
            zoomLevel = parseInt(e.target.value, 10);
            updateCanvasSize();
        });
        brushSlider.addEventListener('input', (e) => {
            brushSize = parseInt(e.target.value, 10);
            brushSizeDisplay.textContent = brushSize;
        });
        
        // NEW: Download button listener
        downloadBtn.addEventListener('click', () => {
            const link = document.createElement('a');
            link.download = 'pixelpub-art.png';
            link.href = canvas.toDataURL('image/png');
            link.click();
        });

        canvas.addEventListener('mousedown', (e) => {
            isDrawing = true;
            applyBrush(getCoords(e).x, getCoords(e).y);
            redrawCanvas();
        });
        
        canvas.addEventListener('mousemove', (e) => { 
            if (isDrawing) {
                applyBrush(getCoords(e).x, getCoords(e).y);
                redrawCanvas();
            } else {
                handleHistoryHover(e);
            }
        });
        
        document.addEventListener('mouseup', () => {
            if (isDrawing) {
                isDrawing = false;
                saveAndLog();
            }
        });
        
        canvas.addEventListener('mouseleave', () => {
             if (isDrawing) {
                isDrawing = false;
                saveAndLog();
            }
            pixelInfoDisplay.style.display = 'none';
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

    function getCoords(event) {
        const rect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;
        return {
            x: Math.floor(mouseX / zoomLevel),
            y: Math.floor(mouseY / zoomLevel)
        };
    }
    
    function handleHistoryHover(event) {
        if (isDrawing) return;
        const coords = getCoords(event);
        if (coords.x !== lastHoveredPixel.x || coords.y !== lastHoveredPixel.y) {
            lastHoveredPixel = coords;
            pixelInfoDisplay.style.display = 'none';
            socket.emit('request_history', { canvas_id: CANVAS_ID, x: coords.x, y: coords.y });
        }
    }
    
    initialize();
});