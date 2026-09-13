document.addEventListener("DOMContentLoaded", function () {
    const calendarEl = document.getElementById("kt_calendar_app");
    if (!calendarEl) return;

    // Отримуємо динамічні дані з HTML data-атрибутів
    const eventsUrl = calendarEl.dataset.eventsUrl;
    const currentLocale = calendarEl.dataset.locale || 'uk';

    const calendar = new FullCalendar.Calendar(calendarEl, {
        // Локалізація (дні/місяці автоматично перекладуться)
        locale: currentLocale,

        headerToolbar: {
            left: "prev,next today",
            center: "title",
            right: "dayGridMonth,timeGridWeek,timeGridDay"
        },

        navLinks: true,
        selectable: true,
        selectMirror: true,
        editable: true,
        dayMaxEvents: true,

        // 🌟 BEST PRACTICE: FullCalendar сам робить GET-запит на цей URL
        // і автоматично передає параметри ?start=2026-07-01&end=2026-08-01
        events: eventsUrl,

        // Перехоплення помилок завантаження подій з API
        eventSourceFailure: function(error) {
            console.error("Failed to fetch calendar events:", error);
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    text: "Could not load calendar events. Please refresh.",
                    icon: "error",
                    buttonsStyling: false,
                    confirmButtonText: "Ok",
                    customClass: { confirmButton: "btn btn-primary" }
                });
            }
        },

        // Вибір діапазону (створення події)
        select: function (arg) {
            const addModalEl = document.getElementById('kt_modal_add_event');
            if (!addModalEl) return;

            const addModal = bootstrap.Modal.getInstance(addModalEl) || new bootstrap.Modal(addModalEl);

            const startDateInput = document.getElementById('kt_calendar_datepicker_start_date');
            const endDateInput = document.getElementById('kt_calendar_datepicker_end_date');

            if (startDateInput) startDateInput.value = arg.startStr;
            if (endDateInput) endDateInput.value = arg.endStr;

            addModal.show();
            calendar.unselect();
        },

        // Клік на існуючу подію
        eventClick: function (arg) {
            const viewModalEl = document.getElementById('kt_modal_view_event');
            if (!viewModalEl) return;

            const viewModal = bootstrap.Modal.getInstance(viewModalEl) || new bootstrap.Modal(viewModalEl);

            const eventNameEl = document.querySelector('[data-kt-calendar="event_name"]');
            if (eventNameEl) eventNameEl.textContent = arg.event.title;

            viewModal.show();
        }
    });

    calendar.render();
});