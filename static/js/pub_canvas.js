document.addEventListener('DOMContentLoaded', () => {
    // --- Setup & Config ---
    const socket = io();
    const canvas = document.getElementById('pixel-canvas');
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const ctx = canvas.getContext('2d');

    const PIXEL_SIZE = 15; // Smaller pixels for larger canvases
    const PUB_ID = canvas.dataset.pubId;
    const CANVAS_ID = canvas.dataset.canvasId;
    const GRID_WIDTH = parseInt(canvas.dataset.canvasWidth, 10);
    const GRID_HEIGHT = parseInt(canvas.dataset.canvasHeight, 10);
    const canvasWidth = PIXEL_SIZE * GRID_WIDTH;
    const canvasHeight = PIXEL_SIZE * GRID_HEIGHT;
    let canvasData = JSON.parse(canvas.dataset.canvasData);

    let selectedColor = '#000000'; // Default color
    let isDrawing = false;
    
    // --- SocketIO Handlers ---
    socket.on('connect', () => {
        socket.emit('join_pub', { pub_id: PUB_ID });
    });

    socket.on('pixel_placed', (data) => {
        canvasData[data.y][data.x] = data.color;
        redrawCanvas();
    });
    
    socket.on('new_message', (data) => {
        appendMessage(data);
    });

    // --- Chat Functions ---
    function appendMessage(data) {
        const messageEl = document.createElement('div');
        messageEl.classList.add('chat-message', 'mb-2');
        messageEl.innerHTML = `
            <img src="/avatar/${data.avatar_id}.png" class="avatar-sm me-2">
            <div>
                <strong class="me-2">${data.username}</strong>
                <small class="text-muted">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</small>
                <p class="mb-0">${data.content}</p>
            </div>`;
        chatMessages.appendChild(messageEl);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll
    }

    // --- Drawing Functions ---
    function redrawCanvas() {
        ctx.clearRect(0, 0, canvasWidth, canvasHeight);
        for (let y = 0; y < GRID_HEIGHT; y++) {
            for (let x = 0; x < GRID_WIDTH; x++) {
                ctx.fillStyle = canvasData[y][x];
                ctx.fillRect(x * PIXEL_SIZE, y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE);
            }
        }
    }

    function placePixel(gridX, gridY) {
        canvasData[gridY][gridX] = selectedColor;
        redrawCanvas();
        socket.emit('place_pixel', { pub_id: PUB_ID, canvas_id: CANVAS_ID, x: gridX, y: gridY, color: selectedColor });
    }
    
    // --- Event Listeners ---
    function initialize() {
        canvas.width = canvasWidth;
        canvas.height = canvasHeight;
        redrawCanvas();
        chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll chat on load

        canvas.addEventListener('mousedown', (e) => {
            isDrawing = true;
            placePixel(getCoords(e).x, getCoords(e).y);
        });
        canvas.addEventListener('mousemove', (e) => {
            if (isDrawing) placePixel(getCoords(e).x, getCoords(e).y);
        });
        document.addEventListener('mouseup', () => isDrawing = false);

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
        return {
            x: Math.floor((event.clientX - rect.left) / PIXEL_SIZE),
            y: Math.floor((event.clientY - rect.top) / PIXEL_SIZE)
        };
    }
    
    initialize();
});