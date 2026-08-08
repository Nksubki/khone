/**
 * تست ماژول‌های جاوااسکریپت (عدد فارسی و تاریخ شمسی) با Node.js
 * اجرا:  node tools/check_js.js
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.join(__dirname, '..');
const failures = [];

// شبیه‌سازی حداقلی محیط مرورگر
global.window = global;
global.document = {
  addEventListener() {},
  querySelectorAll() { return []; },
  createElement() { return { classList: { add() {} }, appendChild() {}, addEventListener() {}, setAttribute() {}, style: {} }; },
  getElementById() { return null; },
  body: { appendChild() {} }
};

function load(file) {
  const code = fs.readFileSync(path.join(root, 'static', 'js', file), 'utf8');
  vm.runInThisContext(code, { filename: file });
}

load('persian-number.js');
load('jalali.js');

function check(condition, message) {
  if (!condition) {
    failures.push(message);
    console.log('  ✗ ' + message);
  }
}

console.log('۱) پارس عدد فارسی');
const NUMBER_CASES = [
  ['100000000', 100000000],
  ['۱۰۰,۰۰۰,۰۰۰', 100000000],
  ['صد میلیون', 100000000],
  ['صد و بیست میلیون', 120000000],
  ['دو میلیارد و سیصد میلیون و پانصد هزار تومان', 2300500000],
  ['۱۰۰ میلیون', 100000000],
  ['نیم میلیارد', 500000000],
  ['۲.۵ میلیون', 2500000],
  ['پنجاه و پنج میلیون و دویست هزار تومان', 55200000],
  ['سه میلیون تومان', 3000000],
  ['یک میلیارد', 1000000000],
  ['هفتصد و پنجاه هزار', 750000],
  ['صدمیلیون', 100000000],
  ['500هزار', 500000],
  ['بیست و پنج', 25],
  ['مبلغ سی و دو میلیون و هشتصد و پنجاه هزار تومان شد', 32850000],
  ['چهارصد و پنجاه میلیون', 450000000],
  ['یک میلیون و پانصد هزار', 1500000],
  ['یک میلیون و نیم', 1500000],
  ['یک میلیون ونیم', 1500000],
  ['دو میلیارد و نیم', 2500000000],
  ['نیم میلیون', 500000],
  ['سی صد میلیون', 300000000],
  ['سه صد و پنجاه هزار', 350000],
  ['پان صد میلیون', 500000000],
  ['100.000.000', 100000000],
  ['۱۲۰,۵۰۰,۰۰۰', 120500000],
  ['۲/۵ میلیون', 2500000],
  ['یک میلیارد و دویست و پنجاه میلیون', 1250000000],
  ['هشتاد و پنج میلیون و چهارصد و پنجاه هزار', 85450000],
  ['دویست و پنجاه میلیون تومان بابت میلگرد', 250000000],
  ['لطفا صد میلیون ثبت کن', 100000000],
  ['سلام خوبی', null],
  ['', null]
];
for (const [text, expected] of NUMBER_CASES) {
  const got = window.KhoneNumber.parse(text);
  check(got === expected, `parse(${JSON.stringify(text)}) = ${got} ≠ ${expected}`);
}

console.log('۲) نمایش عدد و امتیاز گرد بودن');
check(window.KhoneNumber.roundnessScore(100000000) > window.KhoneNumber.roundnessScore(100000123), 'roundnessScore');
check(window.KhoneNumber.roundnessScore(0) === 0, 'roundnessScore صفر');
check(window.KhoneNumber.format(1234567, false) === '1,234,567', 'format latin');
check(window.KhoneNumber.format(1234567, true) === '۱,۲۳۴,۵۶۷', 'format persian');
check(window.KhoneNumber.toWords(230500000) === '۲۳۰ میلیون و ۵۰۰ هزار', 'toWords: ' + window.KhoneNumber.toWords(230500000));

console.log('۳) تبدیل تاریخ');
const DATE_CASES = [
  [[2026, 3, 21], [1405, 1, 1]],
  [[2026, 8, 8], [1405, 5, 17]],
  [[2025, 3, 21], [1404, 1, 1]],
  [[2024, 3, 20], [1403, 1, 1]],
  [[2000, 1, 1], [1378, 10, 11]],
  [[1979, 2, 11], [1357, 11, 22]]
];
for (const [g, j] of DATE_CASES) {
  const got = window.KhoneDate.g2j(g[0], g[1], g[2]);
  check(JSON.stringify(got) === JSON.stringify(j), `g2j ${g} = ${got} ≠ ${j}`);
  const back = window.KhoneDate.j2g(j[0], j[1], j[2]);
  check(JSON.stringify(back) === JSON.stringify(g), `j2g ${j} = ${back} ≠ ${g}`);
}

console.log('۴) رفت و برگشت ۱۹۵۰ تا ۲۰۵۰');
let bad = 0;
let day = Date.UTC(1950, 0, 1);
const end = Date.UTC(2050, 0, 1);
while (day < end) {
  const date = new Date(day);
  const j = window.KhoneDate.g2j(date.getUTCFullYear(), date.getUTCMonth() + 1, date.getUTCDate());
  const g = window.KhoneDate.j2g(j[0], j[1], j[2]);
  if (g[0] !== date.getUTCFullYear() || g[1] !== date.getUTCMonth() + 1 || g[2] !== date.getUTCDate()) {
    bad++;
  }
  if (j[2] > window.KhoneDate.monthDays(j[0], j[1])) { bad++; }
  day += 86400000;
}
check(bad === 0, 'خطای رفت‌وبرگشت: ' + bad);

console.log('۵) کبیسه و طول ماه');
const leaps = [];
for (let y = 1390; y <= 1420; y++) { if (window.KhoneDate.isLeap(y)) { leaps.push(y); } }
console.log('   کبیسه‌ها: ' + leaps.join(', '));
check(JSON.stringify(leaps) === JSON.stringify([1391, 1395, 1399, 1403, 1408, 1412, 1416, 1420]), 'فهرست کبیسه‌ها');

console.log('۶) تجزیه ورودی و روز هفته');
check(JSON.stringify(window.KhoneDate.parseInput('۱۴۰۵/۰۵/۱۷')) === JSON.stringify([1405, 5, 17]), 'parseInput fa');
check(JSON.stringify(window.KhoneDate.parseInput('1405-5-17')) === JSON.stringify([1405, 5, 17]), 'parseInput dash');
check(window.KhoneDate.parseInput('1405/13/01') === null, 'parseInput invalid month');
check(window.KhoneDate.parseInput('1405/12/31') === null, 'parseInput invalid day');
check(window.KhoneDate.weekdayIndex([1405, 5, 17]) === 0, 'شنبه = 0');
check(window.KhoneDate.weekdayIndex([1405, 5, 23]) === 6, 'جمعه = 6');
check(window.KhoneDate.formatJalali([1405, 5, 7]) === '1405/05/07', 'formatJalali');
check(JSON.stringify(window.KhoneDate.addDays([1405, 1, 1], -1)) === JSON.stringify([1404, 12, 29]), 'addDays: ' + window.KhoneDate.addDays([1405, 1, 1], -1));

console.log();
if (failures.length) {
  console.log('نتیجه: ' + failures.length + ' خطا');
  process.exit(1);
}
console.log('نتیجه: همه تست‌های جاوااسکریپت موفق ✓');
