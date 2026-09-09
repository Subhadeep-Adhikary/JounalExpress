document.addEventListener('DOMContentLoaded', () => {
    const camera = document.querySelector('.camera');
    const imageInput = document.querySelector('#image');
    const previewContainer = document.querySelector('#preview-container');
    const previewImage = document.querySelector('#preview-image');
    const removeImageBtn = document.querySelector('#remove-image');

    if (camera && imageInput && previewContainer && previewImage && removeImageBtn) {
        camera.addEventListener('click', () => {
            imageInput.click();
        });

        imageInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewImage.src = e.target.result;
                    previewContainer.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });

        removeImageBtn.addEventListener('click', () => {
            previewImage.src = '';
            previewContainer.style.display = 'none';
            imageInput.value = null;
        });
    }
});

const searchInput = document.getElementById('searchInput');
if (searchInput) {
    searchInput.addEventListener('input', () => {
        const filter = searchInput.value.toLowerCase();
        const fileCards = document.querySelectorAll('.file_card');
        const dateCards = document.querySelectorAll('.date_card');
        
        fileCards.forEach(card => {
            const fileName = card.querySelector('.file').textContent.toLowerCase();
            if (fileName.includes(filter)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
        
        dateCards.forEach(card => {
            const dateText = card.querySelector('.date').textContent.toLowerCase();
            if (dateText.includes(filter)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    });
}
