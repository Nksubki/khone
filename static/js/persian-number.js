/* =========================================================================
   KhoneNumber — تبدیل متن فارسی (تایپی یا گفتاری) به عدد و برعکس
   معادل دقیق ledger/utils/numbers.py است.

   نمونه‌ها:
     «دو میلیارد و سیصد میلیون»  → 2300000000
     «سی صد میلیون»              → 300000000   (اصلاح خطای رایج گفتار)
     «یک میلیون و نیم»           → 1500000
     «100.000.000»               → 100000000
     «۲/۵ میلیون»                → 2500000
   ========================================================================= */
(function (global) {
  'use strict';

  var UNITS = {
    'صفر': 0, 'یک': 1, 'اول': 1, 'دو': 2, 'سه': 3, 'چهار': 4, 'پنج': 5,
    'شش': 6, 'شیش': 6, 'هفت': 7, 'هشت': 8, 'نه': 9, 'ده': 10,
    'یازده': 11, 'دوازده': 12, 'سیزده': 13, 'چهارده': 14, 'پانزده': 15,
    'پونزده': 15, 'شانزده': 16, 'شونزده': 16, 'هفده': 17, 'هیفده': 17,
    'هجده': 18, 'هیجده': 18, 'نوزده': 19,
    'بیست': 20, 'سی': 30, 'چهل': 40, 'پنجاه': 50, 'شصت': 60, 'هفتاد': 70,
    'هشتاد': 80, 'نود': 90,
    'صد': 100, 'یکصد': 100, 'دویست': 200, 'سیصد': 300, 'چهارصد': 400,
    'پانصد': 500, 'پونصد': 500, 'ششصد': 600, 'شیشصد': 600, 'هفتصد': 700,
    'هفصد': 700, 'هشتصد': 800, 'نهصد': 900
  };

  var FRACTIONS = { 'نیم': 0.5, 'ونیم': 0.5, 'ربع': 0.25 };

  var SCALES = {
    'هزار': 1e3, 'هزارتا': 1e3, 'هزاری': 1e3, 'هزارتومان': 1e3, 'هزارتومن': 1e3,
    'میلیون': 1e6, 'ملیون': 1e6, 'میلیونی': 1e6, 'ملیونی': 1e6,
    'میلیارد': 1e9, 'ملیارد': 1e9, 'میلیاردی': 1e9, 'میلیارت': 1e9, 'بیلیون': 1e9,
    'تریلیون': 1e12
  };

  var IGNORED = {
    'و': 1, 'تومان': 1, 'تومن': 1, 'تومانه': 1, 'تومنه': 1, 'ریال': 1,
    'مبلغ': 1, 'حدود': 1, 'تقریبا': 1, 'شد': 1, 'شده': 1, 'است': 1,
    'بود': 1, 'بشه': 1, 'کردم': 1, 'کن': 1, 'بنویس': 1, 'ثبت': 1,
    'لطفا': 1, 'دادم': 1, 'پرداخت': 1, 'پول': 1, 'تا': 1, 'بابت': 1,
    'برای': 1, 'هزینه': 1, 'خرید': 1, 'بشود': 1, 'میشه': 1
  };

  // اصلاح خطاهای رایج تشخیص گفتار (واژه‌های چندپاره)
  var SPLIT_FIXES = [
    ['یک صد', 'صد'],
    ['دو صد', 'دویست'],
    ['دو یست', 'دویست'],
    ['سه صد', 'سیصد'],
    ['سی صد', 'سیصد'],
    ['چهار صد', 'چهارصد'],
    ['پنج صد', 'پانصد'],
    ['پان صد', 'پانصد'],
    ['پون صد', 'پانصد'],
    ['شش صد', 'ششصد'],
    ['شیش صد', 'ششصد'],
    ['هفت صد', 'هفتصد'],
    ['هشت صد', 'هشتصد'],
    ['نه صد', 'نهصد'],
    ['پان زده', 'پانزده'],
    ['شان زده', 'شانزده'],
    ['و نیم', 'ونیم'],
    ['میلیون ها', 'میلیون'],
    ['میلیارد ها', 'میلیارد']
  ];

  var MAX_AMOUNT = 1e15;

  var PERSIAN_DIGITS = '۰۱۲۳۴۵۶۷۸۹';
  var ARABIC_DIGITS = '٠١٢٣٤٥٦٧٨٩';

  var NUMERIC_RE = /^\d+(\.\d+)?$/;
  var THOUSAND_DOT_RE = /^\d{1,3}(\.\d{3})+$/;
  var SLASH_DECIMAL_RE = /^\d+\/\d{1,2}$/;

  function toEnglishDigits(text) {
    if (text === null || text === undefined) { return ''; }
    var out = '';
    var str = String(text);
    for (var i = 0; i < str.length; i++) {
      var ch = str.charAt(i);
      var p = PERSIAN_DIGITS.indexOf(ch);
      var a = ARABIC_DIGITS.indexOf(ch);
      if (p > -1) { out += String(p); }
      else if (a > -1) { out += String(a); }
      else { out += ch; }
    }
    return out;
  }

  function toPersianDigits(text) {
    if (text === null || text === undefined) { return ''; }
    return String(text).replace(/[0-9]/g, function (d) {
      return PERSIAN_DIGITS.charAt(parseInt(d, 10));
    });
  }

  function normalize(text) {
    return toEnglishDigits(text)
      .replace(/ي/g, 'ی').replace(/ك/g, 'ک')
      .replace(/ة/g, 'ه').replace(/ۀ/g, 'ه')
      .replace(/[أإآ]/g, 'ا')
      .replace(/٫/g, '.')
      .replace(/[\u064b-\u0652]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function applySplitFixes(text) {
    var padded = ' ' + text + ' ';
    for (var i = 0; i < SPLIT_FIXES.length; i++) {
      padded = padded.split(' ' + SPLIT_FIXES[i][0] + ' ').join(' ' + SPLIT_FIXES[i][1] + ' ');
    }
    return padded.trim();
  }

  function numericValue(token) {
    if (THOUSAND_DOT_RE.test(token)) { return parseFloat(token.split('.').join('')); }
    if (NUMERIC_RE.test(token)) { return parseFloat(token); }
    if (SLASH_DECIMAL_RE.test(token)) { return parseFloat(token.replace('/', '.')); }
    return null;
  }

  function tokenize(text) {
    var cleaned = normalize(text)
      .replace(/[،]/g, ' ')
      .replace(/,/g, '')
      .replace(/\u200c/g, ' ')
      .replace(/[^\u0600-\u06FF0-9.\/\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
    cleaned = applySplitFixes(cleaned);

    var raw = cleaned.split(' ');
    var tokens = [];
    for (var i = 0; i < raw.length; i++) {
      var token = raw[i].replace(/^\.+|\.+$/g, '');
      if (!token) { continue; }
      if (token.length > 2 && token.charAt(0) === 'و') {
        var rest = token.substring(1);
        if (Object.prototype.hasOwnProperty.call(UNITS, rest) ||
            Object.prototype.hasOwnProperty.call(SCALES, rest)) {
          tokens.push(rest);
          continue;
        }
      }
      tokens.push(token);
    }
    return tokens;
  }

  /** متن را به عدد تبدیل می‌کند؛ اگر عددی پیدا نشود null. */
  function parse(text) {
    if (text === null || text === undefined || text === '') { return null; }
    if (typeof text === 'number') {
      var direct = Math.round(text);
      return (direct > 0 && direct <= MAX_AMOUNT) ? direct : null;
    }

    var tokens = tokenize(text);
    if (!tokens.length) { return null; }

    var total = 0;
    var current = 0;
    var lastScale = 0;
    var found = false;

    for (var i = 0; i < tokens.length; i++) {
      var token = tokens[i];

      if (IGNORED[token]) { continue; }

      var numeric = numericValue(token);
      if (numeric !== null) {
        current += numeric;
        found = true;
        continue;
      }

      if (Object.prototype.hasOwnProperty.call(UNITS, token)) {
        current += UNITS[token];
        found = true;
        continue;
      }

      if (Object.prototype.hasOwnProperty.call(FRACTIONS, token)) {
        var fraction = FRACTIONS[token];
        if (current === 0 && lastScale >= 1000) {
          total += fraction * lastScale;
        } else {
          current = current ? current + fraction : fraction;
        }
        found = true;
        continue;
      }

      if (Object.prototype.hasOwnProperty.call(SCALES, token)) {
        var scale = SCALES[token];
        if (current === 0) { current = 1; }
        current *= scale;
        total += current;
        current = 0;
        lastScale = scale;
        found = true;
        continue;
      }

      // ترکیب چسبیده مثل «صدمیلیون» یا «۵۰۰هزار»
      var matched = false;
      for (var word in SCALES) {
        if (!Object.prototype.hasOwnProperty.call(SCALES, word)) { continue; }
        if (token.length > word.length && token.slice(-word.length) === word) {
          var head = token.substring(0, token.length - word.length);
          var headValue = numericValue(head);
          if (headValue === null && Object.prototype.hasOwnProperty.call(UNITS, head)) {
            headValue = UNITS[head];
          }
          if (headValue === null && Object.prototype.hasOwnProperty.call(FRACTIONS, head)) {
            headValue = FRACTIONS[head];
          }
          if (headValue !== null) {
            current = (current + headValue) * SCALES[word];
            total += current;
            current = 0;
            lastScale = SCALES[word];
            found = true;
            matched = true;
            break;
          }
        }
      }
      if (matched) { continue; }
    }

    if (!found) { return null; }
    total += current;
    if (total <= 0 || total > MAX_AMOUNT) { return null; }
    return Math.round(total);
  }

  function format(value, persian) {
    if (value === null || value === undefined || value === '') { return ''; }
    var number = typeof value === 'number' ? value : parse(value);
    if (number === null) { return ''; }
    var text = String(Math.round(number)).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return persian ? toPersianDigits(text) : text;
  }

  var WORD_SCALES = [
    [1e12, 'هزار میلیارد'],
    [1e9, 'میلیارد'],
    [1e6, 'میلیون'],
    [1e3, 'هزار']
  ];

  function toWords(value, persian) {
    var number = typeof value === 'number' ? value : parse(value);
    if (number === null || isNaN(number)) { return ''; }
    if (number === 0) { return persian === false ? '0' : '۰'; }
    var negative = number < 0;
    number = Math.abs(Math.round(number));
    var parts = [];
    for (var i = 0; i < WORD_SCALES.length; i++) {
      var scale = WORD_SCALES[i][0];
      var label = WORD_SCALES[i][1];
      if (number >= scale) {
        var count = Math.floor(number / scale);
        number = number % scale;
        parts.push(count + ' ' + label);
      }
    }
    if (number) { parts.push(String(number)); }
    var text = (negative ? 'منفی ' : '') + parts.join(' و ');
    return persian === false ? text : toPersianDigits(text);
  }

  /**
   * امتیاز «گرد بودن» مبلغ — برای انتخاب بهترین حدس بین چند نتیجه تشخیص گفتار.
   * مبالغ واقعی هزینه معمولاً مضرب هزار یا میلیون هستند.
   */
  function roundnessScore(value) {
    var number = parseInt(value, 10);
    if (!number || number <= 0) { return 0; }
    var score = 0;
    var table = [[1e6, 3], [1e5, 2], [1e4, 1], [1e3, 1]];
    for (var i = 0; i < table.length; i++) {
      if (number % table[i][0] === 0) { score += table[i][1]; }
    }
    return score;
  }

  global.KhoneNumber = {
    parse: parse,
    format: format,
    toWords: toWords,
    roundnessScore: roundnessScore,
    toEnglishDigits: toEnglishDigits,
    toPersianDigits: toPersianDigits,
    normalize: normalize
  };
})(window);
