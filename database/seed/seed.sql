-- =============================================================================
-- seed.sql — boshlang'ich ma'lumotnomalar (ixtiyoriy, demo uchun)
-- Qoldiq va partiyalar seed qilinmaydi: ular faqat Kirim operatsiyasi orqali
-- (backend biznes qoidalari bilan) yaratiladi.
-- =============================================================================

insert into public.cash_registers (name) values
  ('Kassa Ombor'),
  ('Asosiy kassa'),
  ('Bank hisobi')
on conflict (name) do nothing;

insert into public.products (name, unit, barcode, min_stock, default_sale_price)
select v.name, v.unit::public.product_unit, v.barcode, v.min_stock, v.price
from (values
  ('Aviko kotlet',        'kg',   '4783698595916', 5,  55000),
  ('Aviko kuk paket',     'kg',   '4786840262513', 5,  38000),
  ('Bedro',               'kg',   '4789849913233', 10, 40000),
  ('Burger',              'dona', '4781170548085', 20, 32000),
  ('Burger mini',         'dona', '4789864852852', 20, 1000),
  ('Chips vodiy',         'kg',   '4784689420683', 10, 40000),
  ('Donar Bulochka',      'dona', '4780000000017', 30, 45000),
  ('Hot-dog Bulichka',    'dona', '4780000000024', 30, 40000),
  ('Mayonez Chimboy',     'dona', '4780000000031', 10, 19000),
  ('Moy Frutel',          'litr', '4780000000048', 10, 310000),
  ('Sosiska original',    'dona', '4780000000055', 15, 28000),
  ('Fri - 2.5kg',         'kg',   '4780000000062', 10, 30000)
) as v(name, unit, barcode, min_stock, price)
where not exists (select 1 from public.products p where lower(p.name) = lower(v.name));

insert into public.counterparties (kind, name, phone, address)
select v.kind::public.counterparty_kind, v.name, v.phone, v.address
from (values
  ('supplier', 'Ihlos Gusht',         '+998 99 037 99 99', 'Toshkent'),
  ('supplier', 'Mayonez Sof food',    '+998 90 972 96 30', 'Toshkent'),
  ('supplier', 'Aviko Rovshan aka',   '+998 77 272 66 66', 'Toshkent'),
  ('client',   'Everest Plaza',       '+998 99 553 20 84', 'Zomin tog''i'),
  ('client',   'Elbek Baxt uyi',      '+998 94 004 89 77', 'Baxt uyi'),
  ('client',   'Akbar lavash',        '+998 90 499 21 23', 'Dashtobod'),
  ('client',   'Nodir ko''prik',      '+998 99 980 06 33', 'Ko''prik')
) as v(kind, name, phone, address)
where not exists (
  select 1 from public.counterparties c where c.name = v.name and c.kind = v.kind::public.counterparty_kind
);
