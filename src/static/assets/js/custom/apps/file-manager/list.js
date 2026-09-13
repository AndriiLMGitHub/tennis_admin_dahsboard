"use strict";

// ====================================================================
// 1. ГЛОБАЛЬНІ ФУНКЦІЇ ДЛЯ HTML-ШАБЛОНІВ
// ====================================================================
window.copyToClipboard = function (inputId, button) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const icon = button.querySelector('i');
    input.select();
    navigator.clipboard.writeText(input.value).then(() => {
        if (icon) {
            icon.classList.remove('ki-copy');
            icon.classList.add('ki-check', 'text-success');
            setTimeout(() => {
                icon.classList.remove('ki-check', 'text-success');
                icon.classList.add('ki-copy');
            }, 2000);
        }
    }).catch(err => console.error('Помилка копіювання: ', err));
};

window.confirmRealDelete = function (formId, fileName) {
    Swal.fire({
        title: "Ви впевнені?",
        html: "Ви дійсно хочете видалити <b>" + fileName + "</b>?<br>Ця дія незворотна.",
        icon: "warning",
        showCancelButton: true,
        buttonsStyling: false,
        confirmButtonText: "Так, видалити!",
        cancelButtonText: "Ні, скасувати",
        customClass: {
            confirmButton: "btn fw-bold btn-danger",
            cancelButton: "btn fw-bold btn-active-light-primary"
        }
    }).then(function (result) {
        if (result.value) {
            Swal.fire({
                text: "Видалення...",
                icon: "info",
                allowOutsideClick: false,
                showConfirmButton: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });
            const form = document.getElementById(formId);
            if (form) form.submit();
        }
    });
};

// ====================================================================
// 2. ОСНОВНИЙ МОДУЛЬ ТАБЛИЦІ ФАЙЛІВ
// ====================================================================
var KTFileManagerList = function () {
    var datatable;
    var table;

    const initDatatable = () => {
        // Встановлюємо правильне сортування за датою
        const tableRows = table.querySelectorAll('tbody tr');
        tableRows.forEach(row => {
            const dateRow = row.querySelectorAll('td');
            if (dateRow.length >= 4) {
                const dateCol = dateRow[3];
                if (dateCol && dateCol.innerHTML.trim() !== '') {
                    // Якщо moment.js підключено на сторінці
                    if (typeof moment !== 'undefined') {
                        const realDate = moment(dateCol.innerHTML, "DD MMM YYYY, LT").format();
                        dateCol.setAttribute('data-order', realDate);
                    }
                }
            }
        });

        // Безпечно дістаємо переклади з об'єкта window, із запасними варіантами
        const emptyTitle = (window.FileManagerI18n && window.FileManagerI18n.emptyTitle)
                           ? window.FileManagerI18n.emptyTitle
                           : 'Nothing found.';

        const emptyDesc = (window.FileManagerI18n && window.FileManagerI18n.emptyDesc)
                          ? window.FileManagerI18n.emptyDesc
                          : 'You don\'t have any files uploaded yet.';

        // Ініціалізація DataTables із захистом від подвійного запуску
        datatable = $(table).DataTable({
            "destroy": true,
            "info": true,
            "paging": true,
            "lengthChange": true,
            "lengthMenu": [10, 25, 50, 100],
            'pageLength': 10,
            'order': [],
            'ordering': false,
            'columns': [
                {data: 'checkbox'},
                {data: 'name'},
                {data: 'size'},
                {data: 'date'},
                {data: 'action'},
            ],
            'language': {
                emptyTable: `<div class="d-flex flex-column flex-center py-10">
                    <div class="fs-1 fw-bolder text-dark mb-4">${emptyTitle}</div>
                    <div class="fs-6">${emptyDesc}</div>
                </div>`
            },
            conditionalPaging: true,
            "drawCallback": function (settings) {
                // Оживляємо випадаючі меню після перемальовування
                if (typeof KTMenu !== 'undefined') {
                    KTMenu.createInstances();
                }
            }
        });

        datatable.on('draw', function () {
            toggleToolbars();
            countTotalItems();
        });
    }

    const handleSearchDatatable = () => {
        const filterSearch = document.querySelector('[data-kt-filemanager-table-filter="search"]');
        if (filterSearch) {
            filterSearch.addEventListener('keyup', function (e) {
                datatable.search(e.target.value).draw();
            });
        }
    }

    const toggleToolbars = () => {
        const toolbarBase = document.querySelector('[data-kt-filemanager-table-toolbar="base"]');
        const toolbarSelected = document.querySelector('[data-kt-filemanager-table-toolbar="selected"]');
        const selectedCount = document.querySelector('[data-kt-filemanager-table-select="selected_count"]');

        const allCheckboxes = table.querySelectorAll('tbody [type="checkbox"]');
        let checkedState = false;
        let count = 0;

        allCheckboxes.forEach(c => {
            if (c.checked && c.value && c.value !== "1" && c.value !== "on") {
                checkedState = true;
                count++;
            }
        });

        if (checkedState) {
            if (selectedCount) selectedCount.innerHTML = count;
            if (toolbarBase) toolbarBase.classList.add('d-none');
            if (toolbarSelected) toolbarSelected.classList.remove('d-none');
        } else {
            if (toolbarBase) toolbarBase.classList.remove('d-none');
            if (toolbarSelected) toolbarSelected.classList.add('d-none');
        }
    }

    const initToggleToolbar = () => {
        // Делегування подій: слухаємо всю таблицю
        table.addEventListener('change', function (e) {
            if (e.target && e.target.type === 'checkbox') {
                setTimeout(function () {
                    toggleToolbars();
                }, 50);
            }
        });

        const deleteSelected = document.querySelector('[data-kt-filemanager-table-select="delete_selected"]');
        if (deleteSelected) {
            const newDeleteBtn = deleteSelected.cloneNode(true);
            deleteSelected.parentNode.replaceChild(newDeleteBtn, deleteSelected);

            newDeleteBtn.addEventListener('click', function () {
                const activeCheckboxes = document.querySelectorAll('#kt_file_manager_list tbody [type="checkbox"]:checked');
                const selectedIds = [];
                const rowsToRemove = [];

                activeCheckboxes.forEach(c => {
                    if (c.value && c.value !== "1" && c.value !== "on") {
                        selectedIds.push(c.value);
                        rowsToRemove.push(c.closest('tbody tr'));
                    }
                });

                if (selectedIds.length === 0) return;

                Swal.fire({
                    text: "Ви впевнені, що хочете видалити вибрані файли (" + selectedIds.length + " шт.)?",
                    icon: "warning",
                    showCancelButton: true,
                    buttonsStyling: false,
                    confirmButtonText: "Так, видалити!",
                    cancelButtonText: "Ні, скасувати",
                    customClass: {
                        confirmButton: "btn fw-bold btn-danger",
                        cancelButton: "btn fw-bold btn-active-light-primary"
                    }
                }).then(function (result) {
                    if (result.value) {
                        Swal.fire({
                            text: "Видалення...",
                            icon: "info",
                            allowOutsideClick: false,
                            showConfirmButton: false,
                            didOpen: () => {
                                Swal.showLoading();
                            }
                        });

                        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
                        const csrfToken = csrfInput ? csrfInput.value : '';

                        fetch('bulk-delete/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': csrfToken
                            },
                            body: JSON.stringify({ids: selectedIds})
                        })
                            .then(response => {
                                if (!response.ok) {
                                    return response.json().then(err => {
                                        throw new Error(err.message || `Помилка: ${response.status}`);
                                    })
                                        .catch(() => {
                                            throw new Error(`Помилка сервера: ${response.status}`);
                                        });
                                }
                                return response.json();
                            })
                            .then(data => {
                                if (data.status === 'success') {
                                    Swal.fire({
                                        text: data.message,
                                        icon: "success",
                                        buttonsStyling: false,
                                        confirmButtonText: "Ок",
                                        customClass: {confirmButton: "btn fw-bold btn-primary"}
                                    }).then(function () {
                                        // Видаляємо рядки з UI
                                        rowsToRemove.forEach(row => {
                                            if (row) datatable.row($(row)).remove();
                                        });
                                        datatable.draw(false);

                                        // Скидаємо галочку в шапці
                                        const headerCheckbox = document.querySelector('#kt_file_manager_list thead [type="checkbox"]');
                                        if (headerCheckbox) headerCheckbox.checked = false;

                                        toggleToolbars();
                                        countTotalItems();
                                    });
                                } else {
                                    throw new Error(data.message);
                                }
                            })
                            .catch(error => {
                                Swal.fire({
                                    text: error.message,
                                    icon: "error",
                                    buttonsStyling: false,
                                    confirmButtonText: "Ок",
                                    customClass: {confirmButton: "btn fw-bold btn-danger"}
                                });
                            });
                    }
                });
            });
        }
    }

    const countTotalItems = () => {
        const counter = document.getElementById('kt_file_manager_items_counter');
        if (counter && datatable) {
            counter.innerText = datatable.rows().count() + ' items';
        }
    }

    // Public methods
    return {
        init: function () {
            table = document.querySelector('#kt_file_manager_list');
            if (!table) return;

            initDatatable();
            initToggleToolbar();
            handleSearchDatatable();
            countTotalItems();

            if (typeof KTMenu !== 'undefined') {
                KTMenu.createInstances();
            }
        }
    }
}();

// Ініціалізація після завантаження сторінки
KTUtil.onDOMContentLoaded(function () {
    KTFileManagerList.init();
});