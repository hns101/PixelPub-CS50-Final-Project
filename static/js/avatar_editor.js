document.addEventListener('DOMContentLoaded', () => {
    // --- Setup & Config ---
    const canvas = document.getElementById('avatar-canvas');
    const colorPicker = document.getElementById('color-picker');
    const gridToggle = document.getElementById('grid-toggle');
    const brushSlider = document.getElementById('brush-slider');
    const brushSizeDisplay = document.getElementById('brush-size-display');
    const clearButton = document.getElementById('clear-button');
    const avatarForm = document.getElementById('avatar-form');
    const avatarDataInput = document.getElementById('avatar-data-input');
    const ctx = canvas.getContext('2d');

    const GRID_DIM = 32; // 32x32 grid
    const GRID_COLOR = "#CCCCCC";

    // Set internal canvas resolution. CSS will handle scaling the display.
    canvas.width = GRID_DIM;
    canvas.height = GRID_DIM;
    
    // NEW: Set the visual size of the canvas to be larger
    canvas.style.width = '480px';
    canvas.style.height = '480px';
    canvas.style.imageRendering = 'pixelated';
    
    let avatarData = currentAvatarData || Array(GRID_DIM).fill(null).map(() => Array(GRID_DIM).fill('#FFFFFF'));

    // --- State Management ---
    let selectedColor = colorPicker.value;
    let brushSize = 1;
    let isDrawing = false;

    // --- Drawing & Canvas Functions ---
    function drawGrid() {
        ctx.strokeStyle = GRID_COLOR;
        // Use a small line width relative to the 1x1 pixel grid
        ctx.lineWidth = 0.05;
        for (let i = 0; i <= GRID_DIM; i++) {
            ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, GRID_DIM); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(GRID_DIM, i); ctx.stroke();
        }
    }

    function redrawCanvas() {
        ctx.clearRect(0, 0, GRID_DIM, GRID_DIM);
        
        for (let y = 0; y < GRID_DIM; y++) {
            for (let x = 0; x < GRID_DIM; x++) {
                // Default to white if a pixel has no data (e.g. from older erased data)
                ctx.fillStyle = avatarData[y][x] || '#FFFFFF';
                // Draw each "pixel" as a 1x1 square on the internal canvas
                ctx.fillRect(x, y, 1, 1);
            }
        }
        if (gridToggle.checked) {
            drawGrid();
        }
    }

    // Brush functionality
    function applyBrush(centerX, centerY) {
        const radius = Math.floor((brushSize - 1) / 2);
        for (let y = centerY - radius; y <= centerY + radius; y++) {
            for (let x = centerX - radius; x <= centerX + radius; x++) {
                placePixel(x, y);
            }
        }
    }

    function placePixel(gridX, gridY) {
        if (gridX < 0 || gridX >= GRID_DIM || gridY < 0 || gridY >= GRID_DIM) return;
        
        if (avatarData[gridY][gridX] === selectedColor) return;
        avatarData[gridY][gridX] = selectedColor;
    }
    
    // --- Event Listeners Setup ---
    function initialize() {
        // Fix initial data if it contains nulls
        for(let r=0; r < GRID_DIM; r++) {
            for (let c=0; c < GRID_DIM; c++) {
                if(avatarData[r][c] === null) {
                    avatarData[r][c] = '#FFFFFF';
                }
            }
        }
        redrawCanvas();

        colorPicker.addEventListener('input', (e) => selectedColor = e.target.value);
        gridToggle.addEventListener('change', redrawCanvas);
        clearButton.addEventListener('click', () => {
            avatarData = Array(GRID_DIM).fill(null).map(() => Array(GRID_DIM).fill('#FFFFFF'));
            redrawCanvas();
        });
        
        brushSlider.addEventListener('input', (e) => {
            brushSize = parseInt(e.target.value, 10);
            brushSizeDisplay.textContent = brushSize;
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
            }
        });
        document.addEventListener('mouseup', () => isDrawing = false);
        canvas.addEventListener('mouseleave', () => isDrawing = false);
        
        avatarForm.addEventListener('submit', () => {
            avatarDataInput.value = JSON.stringify(avatarData);
        });
    }

    // Correctly calculates grid coordinates regardless of CSS scaling
    function getCoords(event) {
        const rect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;

        // Calculate mouse position as a ratio of the displayed canvas's dimensions
        const xRatio = mouseX / rect.width;
        const yRatio = mouseY / rect.height;

        // Apply that ratio to the actual internal grid dimensions
        const gridX = Math.floor(xRatio * GRID_DIM);
        const gridY = Math.floor(yRatio * GRID_DIM);
        
        return { x: gridX, y: gridY };
    }
    
    initialize();
});