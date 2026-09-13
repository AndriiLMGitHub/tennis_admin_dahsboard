document.addEventListener('DOMContentLoaded', function () {
    const trigger = document.getElementById('kt_custom_psychology_trigger');
    const content = document.getElementById('kt_custom_psychology_content');
    const wrapper = document.getElementById('kt_custom_psychology_wrapper');

    if (trigger && content && wrapper) {
        trigger.addEventListener('click', function (e) {
            // Блокуємо будь-які зовнішні події та кліки (захист від конфліктів)
            e.preventDefault();
            e.stopPropagation();

            // Перемикаємо класи видимості
            content.classList.toggle('is-open');
            wrapper.classList.toggle('is-open');
        });
    }
});