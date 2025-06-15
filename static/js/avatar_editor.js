document.addEventListener('DOMContentLoaded', () => {
    // --- Setup & Config ---
    const canvas = document.getElementById('avatar-canvas');
    const colorPicker = document.getElementById('color-picker');
    const gridToggle = document.getElementById('grid-toggle');
    const clearButton = document.getElementById('clear-button');
    const avatarForm = document.getElementById('avatar-form');
    const avatarDataInput = document.getElementById('avatar-data-input');
    const ctx = canvas.getContext('2d');

    const PIXEL_SIZE = 15;
    const GRID_DIM = 32; // 32x32 grid
    const canvasSize = PIXEL_SIZE * GRID_DIM;
    const GRID_COLOR = "#CCCCCC";
    
    // Load current avatar data passed from the template, or create a blank one
    let avatarData = currentAvatarData || Array(GRID_DIM).fill(null).map(() => Array(GRID_DIM).fill(null));

    // --- State Management ---
    let selectedColor = colorPicker.value;
    let isDrawing = false;
    let lastDrawnPixel = { x: null, y: null };

    // --- Main Drawing & Redrawing Functions ---
    function drawGrid() {
        ctx.strokeStyle = GRID_COLOR;
        ctx.lineWidth = 1;
        for (let i = 0; i <= canvasSize; i += PIXEL_SIZE) {
            ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvasSize); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(canvasSize, i); ctx.stroke();
        }
    }

    function redrawCanvas() {
        ctx.clearRect(0, 0, canvasSize, canvasSize);
        // White background
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, canvasSize, canvasSize);

        for (let y = 0; y < GRID_DIM; y++) {
            for (let x = 0; x < GRID_DIM; x++) {
                if (avatarData[y][x]) {
                    ctx.fillStyle = avatarData[y][x];
                    ctx.fillRect(x * PIXEL_SIZE, y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE);
                }
            }
        }
        if (gridToggle.checked) {
            drawGrid();
        }
    }

    // --- Event Logic ---
    function placePixel(gridX, gridY) {
        if (lastDrawnPixel.x === gridX && lastDrawnPixel.y === gridY) return;
        avatarData[gridY][gridX] = selectedColor;
        redrawCanvas();
        lastDrawnPixel = { x: gridX, y: gridY };
    }
    
    // --- Event Listeners Setup ---
    function initialize() {
        canvas.width = canvasSize;
        canvas.height = canvasSize;
        redrawCanvas();

        colorPicker.addEventListener('input', (e) => selectedColor = e.target.value);
        gridToggle.addEventListener('change', redrawCanvas);
        clearButton.addEventListener('click', () => {
            avatarData = Array(GRID_DIM).fill(null).map(() => Array(GRID_DIM).fill(null));
            redrawCanvas();
        });

        canvas.addEventListener('mousedown', (e) => {
            isDrawing = true;
            placePixel(getCoords(e).x, getCoords(e).y);
        });
        canvas.addEventListener('mousemove', (e) => {
            if (isDrawing) placePixel(getCoords(e).x, getCoords(e).y);
        });
        canvas.addEventListener('mouseup', () => isDrawing = false);
        canvas.addEventListener('mouseleave', () => isDrawing = false);
        
        // Before submitting the form, serialize the canvas data into the hidden input
        avatarForm.addEventListener('submit', () => {
            avatarDataInput.value = JSON.stringify(avatarData);
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