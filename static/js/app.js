/* =========================================================================
   app.js — رفتارهای عمومی رابط کاربری
   ========================================================================= */
(function () {
  'use strict';

  function on(selector, event, handler) {
    document.querySelectorAll(selector).forEach(function (element) {
      element.addEventListener(event, handler);
    });
  }

  function getCookie(name) {
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) { return parts.pop().split(';').shift(); }
    return '';
  }

  document.addEventListener('DOMContentLoaded', function () {

    var root = document.documentElement;

    /* ---------------- تم روشن/تیره ---------------- */
    function setTheme(value) {
      root.setAttribute('data-theme', value);
      try { localStorage.setItem('khone-theme', value); } catch (e) {}
      syncThemeButtons();
    }
    function syncThemeButtons() {
      var current = root.getAttribute('data-theme') || 'light';
      document.querySelectorAll('[data-theme-set]').forEach(function (button) {
        button.classList.toggle('is-active', button.getAttribute('data-theme-set') === current);
      });
    }
    on('[data-theme-toggle]', 'click', function () {
      setTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    });
    on('[data-theme-set]', 'click', function (event) {
      setTheme(event.currentTarget.getAttribute('data-theme-set'));
    });
    syncThemeButtons();

    /* ---------------- اندازه متن (برای خوانایی بیشتر) ---------------- */
    var FONT_SIZES = ['sm', 'md', 'lg', 'xl', 'xxl'];
    var fontMenu = document.getElementById('font-menu');

    function setFontSize(value) {
      if (FONT_SIZES.indexOf(value) === -1) { value = 'md'; }
      root.setAttribute('data-font', value);
      try { localStorage.setItem('khone-font', value); } catch (e) {}
      syncFontButtons();
    }
    function syncFontButtons() {
      var current = root.getAttribute('data-font') || 'md';
      document.querySelectorAll('[data-font-set]').forEach(function (button) {
        button.classList.toggle('is-active', button.getAttribute('data-font-set') === current);
      });
    }
    function closeFontMenu() {
      if (fontMenu) { fontMenu.hidden = true; }
      document.querySelectorAll('[data-font-menu]').forEach(function (button) {
        button.setAttribute('aria-expanded', 'false');
      });
    }
    on('[data-font-menu]', 'click', function (event) {
      if (!fontMenu) { return; }
      var willOpen = fontMenu.hidden;
      fontMenu.hidden = !willOpen;
      event.currentTarget.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
    });
    on('[data-font-set]', 'click', function (event) {
      setFontSize(event.currentTarget.getAttribute('data-font-set'));
    });
    document.addEventListener('click', function (event) {
      if (!fontMenu || fontMenu.hidden) { return; }
      if (fontMenu.contains(event.target)) { return; }
      if (event.target.closest && event.target.closest('[data-font-menu]')) { return; }
      closeFontMenu();
    });
    syncFontButtons();

    /* ---------------- نوار کناری موبایل (کشویی) ---------------- */
    var sidebar = document.getElementById('sidebar');
    var backdrop = document.querySelector('.sidebar-backdrop');
    var menuButtons = document.querySelectorAll('[data-open-sidebar]');

    function openSidebar() {
      if (sidebar) { sidebar.classList.add('open'); }
      if (backdrop) { backdrop.classList.add('show'); }
      document.body.classList.add('sidebar-open');
      menuButtons.forEach(function (button) { button.setAttribute('aria-expanded', 'true'); });
    }
    function closeSidebar() {
      if (sidebar) { sidebar.classList.remove('open'); }
      if (backdrop) { backdrop.classList.remove('show'); }
      document.body.classList.remove('sidebar-open');
      menuButtons.forEach(function (button) { button.setAttribute('aria-expanded', 'false'); });
    }
    on('[data-open-sidebar]', 'click', function (event) {
      event.stopPropagation();
      if (sidebar && sidebar.classList.contains('open')) { closeSidebar(); }
      else { openSidebar(); }
    });
    on('[data-close-sidebar]', 'click', closeSidebar);

    // با انتخاب هر لینک، منو بسته شود تا نیمه‌باز نماند
    if (sidebar) {
      sidebar.querySelectorAll('a').forEach(function (link) {
        link.addEventListener('click', closeSidebar);
      });
    }
    // اگر صفحه بزرگ شد (چرخش گوشی یا تبلت) وضعیت کشویی پاک شود
    var resizeTimer = null;
    window.addEventListener('resize', function () {
      if (resizeTimer) { clearTimeout(resizeTimer); }
      resizeTimer = setTimeout(function () {
        if (window.innerWidth >= 1024) { closeSidebar(); }
        closeFontMenu();
      }, 120);
    });
    window.addEventListener('orientationchange', closeSidebar);
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') { closeSidebar(); closeFontMenu(); }
    });
    closeSidebar(); // وضعیت اولیه قطعی

    /* ---------------- بستن پیام‌ها ---------------- */
    on('[data-dismiss]', 'click', function (event) {
      var alertBox = event.currentTarget.closest('.alert');
      if (alertBox) { alertBox.remove(); }
    });
    setTimeout(function () {
      document.querySelectorAll('.alert-success, .alert-info').forEach(function (box) {
        box.style.transition = 'opacity .4s';
        box.style.opacity = '0';
        setTimeout(function () { box.remove(); }, 400);
      });
    }, 6000);

    /* ---------------- نمایش/پنهان کردن فیلترها ---------------- */
    var filterForm = document.getElementById('filter-form');
    on('[data-toggle-filters]', 'click', function () {
      if (filterForm) { filterForm.classList.toggle('collapsed'); }
    });
    if (filterForm && window.innerWidth < 820) {
      var hasActive = document.querySelector('.check-chip input:checked');
      if (!hasActive) { filterForm.classList.add('collapsed'); }
    }

    /* ---------------- فیلدهای مبلغ: جداکننده هزارگان ---------------- */
    function formatAmountInput(input) {
      if (!window.KhoneNumber) { return; }
      var raw = window.KhoneNumber.toEnglishDigits(input.value || '').replace(/[^\d]/g, '');
      if (!raw) {
        input.value = '';
        return;
      }
      input.value = window.KhoneNumber.format(parseInt(raw, 10), false);
    }

    document.querySelectorAll('[data-amount]').forEach(function (input) {
      input.addEventListener('input', function () {
        var hasWords = /[\u0600-\u06FF]/.test(input.value);
        // اگر کاربر با صدا/کیبورد فارسی حرف نوشت، جهت فیلد راست‌به‌چپ شود
        input.style.direction = hasWords ? 'rtl' : 'ltr';
        if (!hasWords) { formatAmountInput(input); }
        updateAmountWords();
      });
      input.addEventListener('blur', function () {
        if (window.KhoneNumber) {
          var parsed = window.KhoneNumber.parse(input.value);
          if (parsed !== null) { input.value = window.KhoneNumber.format(parsed, false); }
        }
        updateAmountWords();
      });
    });

    /* ---------------- نمایش مبلغ به حروف ---------------- */
    var amountWordsBox = document.getElementById('amount-words');
    var mainAmountInput = document.querySelector('#tx-form [data-amount]');

    function updateAmountWords() {
      if (!amountWordsBox || !mainAmountInput || !window.KhoneNumber) { return; }
      var raw = mainAmountInput.value;
      var value = window.KhoneNumber.parse(raw);
      if (value === null) {
        amountWordsBox.textContent = '';
        amountWordsBox.classList.remove('is-converted');
        return;
      }
      var hasWords = /[\u0600-\u06FF]/.test(raw);
      amountWordsBox.classList.toggle('is-converted', hasWords);
      amountWordsBox.textContent = hasWords
        ? window.KhoneNumber.format(value, true) + ' تومان  (' + window.KhoneNumber.toWords(value) + ')'
        : window.KhoneNumber.toWords(value) + ' تومان';
    }
    updateAmountWords();

    /* ---------------- دکمه‌های افزودن سریع مبلغ ---------------- */
    on('[data-amount-add]', 'click', function (event) {
      if (!mainAmountInput || !window.KhoneNumber) { return; }
      var add = parseInt(event.currentTarget.getAttribute('data-amount-add'), 10) || 0;
      var current = window.KhoneNumber.parse(mainAmountInput.value) || 0;
      mainAmountInput.value = window.KhoneNumber.format(current + add, false);
      updateAmountWords();
    });
    on('[data-amount-clear]', 'click', function () {
      if (!mainAmountInput) { return; }
      mainAmountInput.value = '';
      updateAmountWords();
      mainAmountInput.focus();
    });

    /* ---------------- تاریخ شمسی ---------------- */
    on('[data-open-calendar]', 'click', function (event) {
      var selector = event.currentTarget.getAttribute('data-open-calendar');
      var input = document.querySelector(selector);
      if (input && window.KhoneDate) { window.KhoneDate.openPicker(input); }
    });

    document.querySelectorAll('[data-jalali-date]').forEach(function (input) {
      input.addEventListener('focus', function () {
        if (window.KhoneDate && window.innerWidth >= 560) {
          window.KhoneDate.openPicker(input);
        }
      });
      input.addEventListener('input', function () {
        if (!window.KhoneNumber) { return; }
        var digits = window.KhoneNumber.toEnglishDigits(input.value).replace(/[^\d/]/g, '');
        // درج خودکار اسلش: 14050517 → 1405/05/17
        var onlyDigits = digits.replace(/\//g, '');
        if (digits.indexOf('/') === -1 && onlyDigits.length >= 5) {
          var out = onlyDigits.substring(0, 4);
          if (onlyDigits.length > 4) { out += '/' + onlyDigits.substring(4, 6); }
          if (onlyDigits.length > 6) { out += '/' + onlyDigits.substring(6, 8); }
          digits = out;
        }
        input.value = digits;
        updateDatePreview();
      });
      input.addEventListener('change', updateDatePreview);
    });

    var datePreview = document.getElementById('date-preview');
    var dateInput = document.querySelector('#tx-form [data-jalali-date]');

    function updateDatePreview() {
      if (!datePreview || !dateInput || !window.KhoneDate) { return; }
      var parts = window.KhoneDate.parseInput(dateInput.value);
      if (!parts) {
        datePreview.textContent = dateInput.value ? 'قالب تاریخ درست نیست (نمونه: ۱۴۰۵/۰۵/۱۷)' : '';
        return;
      }
      var names = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه'];
      datePreview.textContent = names[window.KhoneDate.weekdayIndex(parts)] + ' '
        + window.KhoneDate.formatLong(parts);
    }
    updateDatePreview();

    on('[data-date-set]', 'click', function (event) {
      if (!dateInput || !window.KhoneDate) { return; }
      var delta = parseInt(event.currentTarget.getAttribute('data-date-set'), 10) || 0;
      var target = window.KhoneDate.addDays(window.KhoneDate.todayJalali(), delta);
      dateInput.value = window.KhoneDate.formatJalali(target);
      updateDatePreview();
    });

    /* ---------------- ماسک ساعت ---------------- */
    document.querySelectorAll('[data-time-mask]').forEach(function (input) {
      input.addEventListener('input', function () {
        if (!window.KhoneNumber) { return; }
        var digits = window.KhoneNumber.toEnglishDigits(input.value).replace(/[^\d]/g, '').substring(0, 4);
        if (digits.length >= 3) {
          input.value = digits.substring(0, 2) + ':' + digits.substring(2);
        } else {
          input.value = digits;
        }
      });
    });

    /* ---------------- جایگزین :has() برای مرورگرهای قدیمی‌تر ---------------- */
    function syncCheckedClass(selector, wrapperSelector) {
      document.querySelectorAll(selector).forEach(function (input) {
        function apply() {
          var group = input.name
            ? document.querySelectorAll('input[name="' + input.name + '"]')
            : [input];
          Array.prototype.forEach.call(group, function (member) {
            var wrapper = member.closest(wrapperSelector);
            if (wrapper) { wrapper.classList.toggle('is-checked', member.checked); }
          });
        }
        input.addEventListener('change', apply);
        apply();
      });
    }
    syncCheckedClass('.kind-option input', '.kind-option');
    syncCheckedClass('.check-chip input', '.check-chip');
    syncCheckedClass('.icon-tile input', '.icon-tile');
    syncCheckedClass('.color-swatch input', '.color-swatch');

    /* ---------------- انتخاب سریع دسته‌بندی ---------------- */
    var categorySelect = document.querySelector('#tx-form select[name="category"]');

    function syncCategoryChips() {
      if (!categorySelect) { return; }
      document.querySelectorAll('.cat-chip').forEach(function (chip) {
        chip.classList.toggle('selected', chip.getAttribute('data-cat-id') === categorySelect.value);
      });
    }
    on('.cat-chip', 'click', function (event) {
      if (!categorySelect) { return; }
      categorySelect.value = event.currentTarget.getAttribute('data-cat-id');
      categorySelect.dispatchEvent(new Event('change', { bubbles: true }));
      syncCategoryChips();
    });
    if (categorySelect) {
      categorySelect.addEventListener('change', syncCategoryChips);
      syncCategoryChips();
    }

    /* ---------------- فیلتر دسته‌ها بر اساس نوع رکورد ---------------- */
    var kindRadios = document.querySelectorAll('#tx-form input[name="kind"]');

    function filterCategoriesByKind() {
      if (!kindRadios.length || !categorySelect) { return; }
      var kind = 'expense';
      kindRadios.forEach(function (radio) { if (radio.checked) { kind = radio.value; } });

      Array.prototype.forEach.call(categorySelect.options, function (option) {
        if (!option.value) { return; }
        var optionKind = option.getAttribute('data-kind');
        var show = !optionKind || optionKind === kind;
        option.hidden = !show;
        option.disabled = !show;
      });
      var selectedOption = categorySelect.options[categorySelect.selectedIndex];
      if (selectedOption && selectedOption.disabled) { categorySelect.value = ''; }

      document.querySelectorAll('.cat-chip').forEach(function (chip) {
        var chipKind = chip.getAttribute('data-cat-kind');
        chip.style.display = (!chipKind || chipKind === kind) ? '' : 'none';
      });
      syncCategoryChips();
    }
    kindRadios.forEach(function (radio) {
      radio.addEventListener('change', filterCategoriesByKind);
    });
    filterCategoriesByKind();

    /* ---------------- ساخت سریع دسته‌بندی ---------------- */
    var newcatBox = document.getElementById('newcat-box');
    on('[data-open-newcat]', 'click', function () {
      if (!newcatBox) { return; }
      newcatBox.hidden = !newcatBox.hidden;
      if (!newcatBox.hidden) {
        var nameInput = document.getElementById('newcat-name');
        if (nameInput) { nameInput.focus(); }
      }
    });
    on('[data-close-newcat]', 'click', function () {
      if (newcatBox) { newcatBox.hidden = true; }
    });

    var saveCategoryBtn = document.getElementById('newcat-save');
    if (saveCategoryBtn) {
      saveCategoryBtn.addEventListener('click', function () {
        var nameInput = document.getElementById('newcat-name');
        var iconInput = document.getElementById('newcat-icon');
        var messageBox = document.getElementById('newcat-msg');
        var name = (nameInput && nameInput.value || '').trim();
        if (!name) {
          if (messageBox) { messageBox.textContent = 'نام دسته را بنویسید.'; }
          return;
        }
        var kind = 'expense';
        kindRadios.forEach(function (radio) { if (radio.checked) { kind = radio.value; } });

        var body = new FormData();
        body.append('name', name);
        body.append('icon', (iconInput && iconInput.value) || 'box');
        body.append('kind', kind);

        saveCategoryBtn.disabled = true;
        if (messageBox) { messageBox.textContent = 'در حال ساخت…'; }

        fetch(saveCategoryBtn.getAttribute('data-url') || '/dastebandi/sari/', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
          body: body,
          credentials: 'same-origin'
        })
          .then(function (response) { return response.json(); })
          .then(function (data) {
            saveCategoryBtn.disabled = false;
            if (!data.ok) {
              if (messageBox) { messageBox.textContent = data.error || 'ساخت دسته ممکن نشد.'; }
              return;
            }
            if (categorySelect) {
              var exists = false;
              Array.prototype.forEach.call(categorySelect.options, function (option) {
                if (option.value === String(data.id)) { exists = true; }
              });
              if (!exists) {
                var option = document.createElement('option');
                option.value = String(data.id);
                option.textContent = data.label;
                option.setAttribute('data-kind', data.kind || kind);
                categorySelect.appendChild(option);
                addCategoryChip(data);
              }
              categorySelect.value = String(data.id);
              categorySelect.dispatchEvent(new Event('change', { bubbles: true }));
            }
            if (messageBox) {
              messageBox.textContent = data.existing
                ? 'این دسته از قبل وجود داشت و انتخاب شد.'
                : 'دسته «' + name + '» ساخته و انتخاب شد';
            }
            if (nameInput) { nameInput.value = ''; }
            setTimeout(function () { if (newcatBox) { newcatBox.hidden = true; } }, 1200);
          })
          .catch(function () {
            saveCategoryBtn.disabled = false;
            if (messageBox) { messageBox.textContent = 'خطای شبکه؛ دوباره تلاش کنید.'; }
          });
      });
    }

    /* ---------------- پیش‌نمایش آیکن دسته جدید ---------------- */
    var newcatIconSelect = document.getElementById('newcat-icon');
    var newcatPreview = document.getElementById('newcat-preview');

    function setUseHref(svgWrapper, key) {
      if (!svgWrapper) { return; }
      var use = svgWrapper.querySelector('use');
      if (!use) { return; }
      use.setAttribute('href', '#i-' + key);
      use.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', '#i-' + key);
    }

    function updateNewcatPreview() {
      if (!newcatIconSelect) { return; }
      setUseHref(newcatPreview, newcatIconSelect.value || 'box');
    }
    if (newcatIconSelect) {
      newcatIconSelect.addEventListener('change', updateNewcatPreview);
      updateNewcatPreview();
    }

    /* ---------------- افزودن چیپ دسته جدید بعد از ساخت سریع ---------------- */
    function addCategoryChip(data) {
      var container = document.getElementById('cat-quick');
      if (!container || !data) { return; }
      var chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip cat-chip';
      chip.setAttribute('data-cat-id', String(data.id));
      chip.setAttribute('data-cat-kind', data.kind || 'expense');
      if (data.color) { chip.style.setProperty('--chip-color', data.color); }
      chip.innerHTML =
        '<svg class="icon icon-sm" aria-hidden="true"><use href="#i-' +
        (data.icon || 'box') + '"></use></svg> ';
      chip.appendChild(document.createTextNode(data.label || ''));
      chip.addEventListener('click', function () {
        if (!categorySelect) { return; }
        categorySelect.value = chip.getAttribute('data-cat-id');
        categorySelect.dispatchEvent(new Event('change', { bubbles: true }));
        syncCategoryChips();
      });
      container.appendChild(chip);
    }

    /* ---------------- انتخابگر آیکن در فرم دسته‌بندی ---------------- */
    var iconTiles = document.querySelectorAll('.icon-picker .icon-tile input');
    if (iconTiles.length) {
      // آیکن انتخاب‌شده را در دید کاربر قرار می‌دهد
      var checked = document.querySelector('.icon-picker .icon-tile input:checked');
      if (checked && checked.closest) {
        var tile = checked.closest('.icon-tile');
        if (tile && tile.scrollIntoView) {
          try { tile.scrollIntoView({ block: 'nearest', inline: 'nearest' }); } catch (e) {}
        }
      }
    }

    /* ---------------- جلوگیری از ارسال دوباره فرم ---------------- */
    document.querySelectorAll('form').forEach(function (form) {
      form.addEventListener('submit', function () {
        var button = form.querySelector('button[type="submit"]');
        if (!button || form.getAttribute('method') === 'get') { return; }
        setTimeout(function () {
          button.disabled = true;
          button.style.opacity = '.7';
        }, 10);
        setTimeout(function () {
          button.disabled = false;
          button.style.opacity = '';
        }, 6000);
      });
    });
  });
})();
