/**
 * KKU Shooting Club - Universal Image Cropper Helper
 * Uses Cropper.js to crop images directly in the browser before upload.
 */

let cropperInstance = null;
let currentFileInput = null;
let currentCropOptions = null;
let cropModalBootstrap = null;

// Ensure Crop Modal HTML exists in document
function ensureCropModalDOM() {
    if (document.getElementById('kkuCropModal')) return;

    const modalHTML = `
    <div class="modal fade" id="kkuCropModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
        <div class="modal-dialog modal-dialog-centered modal-lg">
            <div class="modal-content" style="background: #0b1120; border: 1.5px solid rgba(245, 158, 11, 0.4); box-shadow: 0 10px 40px rgba(0,0,0,0.85); color: #e2e8f0;">
                <div class="modal-header border-secondary py-3">
                    <div class="d-flex align-items-center gap-2">
                        <i class="bi bi-crop text-warning fs-4"></i>
                        <div>
                            <h5 class="modal-title fw-bold text-white mb-0" id="kkuCropModalTitle">ปรับแต่งและครอบตัดรูปภาพ</h5>
                            <div class="small text-secondary" style="font-size: 0.78rem;">ลาก ปรับขนาด หรือหมุนรูปตามต้องการก่อนบันทึก</div>
                        </div>
                    </div>
                    <button type="button" class="btn-close btn-close-white" onclick="cancelImageCrop()" aria-label="Close"></button>
                </div>

                <div class="modal-body p-3 p-md-4">
                    <!-- Cropper Canvas Container -->
                    <div style="width: 100%; height: 380px; max-height: 55vh; background: #020617; border-radius: 12px; overflow: hidden; position: relative; border: 1px solid rgba(255,255,255,0.1);">
                        <img id="kkuCropSourceImage" src="" style="display: block; max-width: 100%;" alt="To Crop">
                    </div>

                    <!-- Toolbar & Controls -->
                    <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mt-3 p-2 rounded" style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255,255,255,0.06);">
                        <!-- Aspect Ratio Presets -->
                        <div class="d-flex gap-1" id="kkuCropAspectGroup">
                            <button type="button" class="btn btn-sm btn-outline-info active" id="btnCropSquare" onclick="setCropRatio(1/1)">
                                <i class="bi bi-square"></i> 1:1 รูปโปรไฟล์
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-info" id="btnCropPortrait" onclick="setCropRatio(3/4)">
                                <i class="bi bi-file-person"></i> 3:4 บัตร
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-info" id="btnCropFree" onclick="setCropRatio(NaN)">
                                <i class="bi bi-bounding-box"></i> อิสระ
                            </button>
                        </div>

                        <!-- Rotation & Transform Tools -->
                        <div class="d-flex gap-1">
                            <button type="button" class="btn btn-sm btn-dark text-white border-secondary" onclick="rotateCrop(-90)" title="หมุนซ้าย 90°">
                                <i class="bi bi-arrow-counterclockwise"></i>
                            </button>
                            <button type="button" class="btn btn-sm btn-dark text-white border-secondary" onclick="rotateCrop(90)" title="หมุนขวา 90°">
                                <i class="bi bi-arrow-clockwise"></i>
                            </button>
                            <button type="button" class="btn btn-sm btn-dark text-white border-secondary" onclick="zoomCrop(0.1)" title="ซูมเข้า">
                                <i class="bi bi-zoom-in"></i>
                            </button>
                            <button type="button" class="btn btn-sm btn-dark text-white border-secondary" onclick="zoomCrop(-0.1)" title="ซูมออก">
                                <i class="bi bi-zoom-out"></i>
                            </button>
                            <button type="button" class="btn btn-sm btn-dark text-white border-secondary" onclick="resetCrop()" title="คืนค่าเดิม">
                                <i class="bi bi-arrow-repeat"></i>
                            </button>
                        </div>
                    </div>
                </div>

                <div class="modal-footer border-secondary justify-content-between py-2 px-3">
                    <button type="button" class="btn btn-outline-secondary px-3" onclick="cancelImageCrop()">
                        ยกเลิก
                    </button>
                    <button type="button" class="btn btn-success fw-bold px-4 d-flex align-items-center gap-1 shadow" onclick="applyImageCrop()">
                        <i class="bi bi-check2-circle fs-5"></i> ใช้งานรูปภาพนี้
                    </button>
                </div>
            </div>
        </div>
    </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

/**
 * Trigger crop modal when user selects a file
 * @param {HTMLInputElement} inputEl
 * @param {Object} options
 */
function handleImageSelectForCrop(inputEl, options = {}) {
    if (!inputEl.files || !inputEl.files[0]) return;

    const file = inputEl.files[0];
    if (!file.type.startsWith('image/')) {
        alert('กรุณาเลือกไฟล์รูปภาพเท่านั้น (.jpg, .png, .jpeg)');
        inputEl.value = '';
        return;
    }

    ensureCropModalDOM();
    currentFileInput = inputEl;
    currentCropOptions = Object.assign({
        aspectRatio: 1 / 1, // Default to 1:1 for profile pictures
        isSlip: false,
        modalTitle: 'ปรับแต่งและครอบตัดรูปภาพ',
        previewImgId: null,
        placeholderId: null,
        statusTextId: null
    }, options);

    // Update modal title
    document.getElementById('kkuCropModalTitle').innerText = currentCropOptions.modalTitle;

    // Show or hide aspect ratio buttons depending on type
    const btnSquare = document.getElementById('btnCropSquare');
    const btnPortrait = document.getElementById('btnCropPortrait');
    const btnFree = document.getElementById('btnCropFree');

    if (currentCropOptions.isSlip) {
        // For slips: default to free form
        currentCropOptions.aspectRatio = NaN;
        btnSquare.classList.remove('active');
        btnPortrait.classList.remove('active');
        btnFree.classList.add('active');
    } else {
        // For avatars: default to 1:1
        btnSquare.classList.add('active');
        btnPortrait.classList.remove('active');
        btnFree.classList.remove('active');
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        const cropImg = document.getElementById('kkuCropSourceImage');
        cropImg.src = e.target.result;

        if (!cropModalBootstrap) {
            cropModalBootstrap = new bootstrap.Modal(document.getElementById('kkuCropModal'));
        }
        cropModalBootstrap.show();

        // Initialize Cropper.js after modal is shown
        const modalEl = document.getElementById('kkuCropModal');
        const onModalShown = function() {
            modalEl.removeEventListener('shown.bs.modal', onModalShown);
            if (cropperInstance) {
                cropperInstance.destroy();
            }

            cropperInstance = new Cropper(cropImg, {
                aspectRatio: currentCropOptions.aspectRatio,
                viewMode: 1,
                dragMode: 'move',
                autoCropArea: 0.9,
                restore: false,
                guides: true,
                center: true,
                highlight: false,
                cropBoxMovable: true,
                cropBoxResizable: true,
                toggleDragModeOnDblclick: false,
                background: true
            });
        };

        modalEl.addEventListener('shown.bs.modal', onModalShown);
    };

    reader.readAsDataURL(file);
}

function setCropRatio(ratio) {
    if (!cropperInstance) return;
    cropperInstance.setAspectRatio(ratio);

    const btnSquare = document.getElementById('btnCropSquare');
    const btnPortrait = document.getElementById('btnCropPortrait');
    const btnFree = document.getElementById('btnCropFree');

    btnSquare.classList.toggle('active', ratio === 1);
    btnPortrait.classList.toggle('active', ratio === 3/4);
    btnFree.classList.toggle('active', isNaN(ratio));
}

function rotateCrop(deg) {
    if (cropperInstance) cropperInstance.rotate(deg);
}

function zoomCrop(delta) {
    if (cropperInstance) cropperInstance.zoom(delta);
}

function resetCrop() {
    if (cropperInstance) cropperInstance.reset();
}

function cancelImageCrop() {
    if (cropperInstance) {
        cropperInstance.destroy();
        cropperInstance = null;
    }
    if (cropModalBootstrap) {
        cropModalBootstrap.hide();
    }
    // If no existing file, clear input
    if (currentFileInput && (!currentFileInput.files || currentFileInput.files.length === 0)) {
        currentFileInput.value = '';
    }
}

function applyImageCrop() {
    if (!cropperInstance || !currentFileInput) return;

    // Get cropped canvas
    const canvas = cropperInstance.getCroppedCanvas({
        maxWidth: 1200,
        maxHeight: 1200,
        fillColor: '#ffffff',
        imageSmoothingEnabled: true,
        imageSmoothingQuality: 'high'
    });

    if (!canvas) {
        alert('เกิดข้อผิดพลาดในการครอบตัดรูปภาพ');
        return;
    }

    canvas.toBlob(function(blob) {
        if (!blob) return;

        const originalName = (currentFileInput.files && currentFileInput.files[0]) ? currentFileInput.files[0].name : 'cropped_image.jpg';
        const fileExt = originalName.split('.').pop().toLowerCase();
        const mimeType = fileExt === 'png' ? 'image/png' : 'image/jpeg';
        const newFile = new File([blob], originalName, { type: mimeType });

        // Replace files in input via DataTransfer
        try {
            const dt = new DataTransfer();
            dt.items.add(newFile);
            currentFileInput.files = dt.files;
        } catch (e) {
            console.log('DataTransfer fallback err:', e);
        }

        // Update preview image on the page
        if (currentCropOptions.previewImgId) {
            const previewEl = document.getElementById(currentCropOptions.previewImgId);
            if (previewEl) {
                previewEl.src = canvas.toDataURL(mimeType, 0.92);
                previewEl.style.display = 'block';
            }
        }

        // Hide placeholder icon if present
        if (currentCropOptions.placeholderId) {
            const placeholderEl = document.getElementById(currentCropOptions.placeholderId);
            if (placeholderEl) {
                placeholderEl.style.display = 'none';
            }
        }

        // Update status text if present
        if (currentCropOptions.statusTextId) {
            const statusEl = document.getElementById(currentCropOptions.statusTextId);
            if (statusEl) {
                statusEl.innerText = 'แนบแล้ว (ครอบตัดเรียบร้อย): ' + originalName;
            }
        }

        // Cleanup & Close modal
        cropperInstance.destroy();
        cropperInstance = null;
        if (cropModalBootstrap) {
            cropModalBootstrap.hide();
        }
    }, 'image/jpeg', 0.92);
}
