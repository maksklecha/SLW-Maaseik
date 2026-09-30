-- 100% FAKE demo data. Never put real customer data in this repo.
-- batch 0 = history (already known), batch 1 = "New data arrives" in the demo.

INSERT INTO merchants (name, description) VALUES
 ('Little Stars Childwear', 'Clothing shop for babies and children aged 0-8'),
 ('Prenatal Antwerpen',     'Maternity clothing and baby gear store'),
 ('Brussels Airlines',      'Airline, flights from Brussels Airport'),
 ('Booking.com',            'Online hotel booking platform'),
 ('Hotel Gracery Tokyo',    'Hotel in Tokyo, Japan'),
 ('JR East',                'Japanese rail company, train tickets'),
 ('Lawson Narita',          'Convenience store in Japan'),
 ('Brico Liège',            'DIY and hardware store: tools, paint and building materials'),
 ('Carrelages Dupont',      'Tile shop for floor and wall tiles'),
 ('Colruyt',                'Supermarket'),
 ('Delhaize',               'Supermarket'),
 ('Spotify',                'Music streaming subscription'),
 ('Engie',                  'Energy provider');

-- ===== 3 example customers ====================================================
INSERT INTO customers VALUES
 ('C001', 'Yusuf Demir',   31, 'M', 'Nurse (night shifts)',       'Antwerpen', 'nl', 0, 2900, 'app',   15, 17),
 ('C002', 'Lotte Peeters', 27, 'F', 'Software developer',         'Gent',      'en', 0, 3600, 'app',   19, 22),
 ('C003', 'Marc Dubois',   68, 'M', 'Retired teacher, homeowner', 'Liège',     'fr', 2, 2450, 'email',  9, 11);

-- ===== Transactions ============================================================
INSERT INTO transactions (customer_id, ts, merchant, amount, currency, amount_eur, country, batch, released) VALUES
 -- Yusuf: no children, then repeated visits to a childwear shop -> expecting a child
 ('C001', '2026-09-02 18:10', 'Colruyt',                84.20, 'EUR',  84.20, 'BE', 0, 1),
 ('C001', '2026-09-06 16:30', 'Little Stars Childwear', 55.00, 'EUR',  55.00, 'BE', 0, 1),
 ('C001', '2026-09-14 09:00', 'Engie',                 140.00, 'EUR', 140.00, 'BE', 0, 1),
 ('C001', '2026-09-18 16:05', 'Little Stars Childwear', 60.00, 'EUR',  60.00, 'BE', 1, 0),
 ('C001', '2026-09-23 15:40', 'Little Stars Childwear', 48.00, 'EUR',  48.00, 'BE', 1, 0),
 ('C001', '2026-09-27 11:20', 'Prenatal Antwerpen',     80.00, 'EUR',  80.00, 'BE', 1, 0),
 ('C001', '2026-09-29 16:15', 'Little Stars Childwear', 77.00, 'EUR',  77.00, 'BE', 1, 0),
 -- Lotte: flights + hotels, then paying in yen in Japan -> international travel
 ('C002', '2026-09-01 19:30', 'Delhaize',               62.50, 'EUR',  62.50, 'BE', 0, 1),
 ('C002', '2026-09-03 20:15', 'Brussels Airlines',     570.00, 'EUR', 570.00, 'BE', 0, 1),
 ('C002', '2026-09-05 08:00', 'Spotify',                11.99, 'EUR',  11.99, 'BE', 0, 1),
 ('C002', '2026-09-12 21:00', 'Booking.com',           310.00, 'EUR', 310.00, 'BE', 1, 0),
 ('C002', '2026-09-15 20:40', 'Brussels Airlines',     570.00, 'EUR', 570.00, 'BE', 1, 0),
 ('C002', '2026-09-20 21:10', 'Booking.com',           290.00, 'EUR', 290.00, 'BE', 1, 0),
 ('C002', '2026-09-28 19:50', 'Booking.com',           300.00, 'EUR', 300.00, 'BE', 1, 0),
 ('C002', '2026-09-30 09:05', 'Lawson Narita',        2400.00, 'JPY',  15.10, 'JP', 1, 0),
 ('C002', '2026-09-30 10:10', 'JR East',             29650.00, 'JPY', 186.40, 'JP', 1, 0),
 ('C002', '2026-09-30 15:00', 'Hotel Gracery Tokyo', 64000.00, 'JPY', 402.50, 'JP', 1, 0),
 -- Marc (68): repeated DIY/building purchases -> home renovation (+ budget pressure)
 ('C003', '2026-09-01 10:00', 'Delhaize',               87.00, 'EUR',  87.00, 'BE', 0, 1),
 ('C003', '2026-09-04 10:30', 'Brico Liège',            90.00, 'EUR',  90.00, 'BE', 0, 1),
 ('C003', '2026-09-20 09:00', 'Engie',                 160.00, 'EUR', 160.00, 'BE', 0, 1),
 ('C003', '2026-09-10 10:15', 'Brico Liège',           125.00, 'EUR', 125.00, 'BE', 1, 0),
 ('C003', '2026-09-17 11:00', 'Carrelages Dupont',    1150.00, 'EUR',1150.00, 'BE', 1, 0),
 ('C003', '2026-09-21 10:45', 'Brico Liège',           110.00, 'EUR', 110.00, 'BE', 1, 0),
 ('C003', '2026-09-27 09:30', 'Brico Liège',            95.00, 'EUR',  95.00, 'BE', 1, 0);

-- ===== Behavioral data (in-app actions) ============================================
INSERT INTO app_events (customer_id, ts, event, detail, batch, released) VALUES
 ('C001', '2026-09-20 16:00', 'viewed_child_savings',    'Opened the child savings page',       1, 0),
 ('C001', '2026-09-28 15:30', 'viewed_family_insurance', 'Opened the family insurance page',    1, 0),
 ('C002', '2026-09-16 21:00', 'viewed_travel_insurance', 'Opened the travel insurance page',    1, 0),
 ('C003', '2026-08-29 09:10', 'balance_check_month_end', 'Checked balance',                     0, 1),
 ('C003', '2026-08-30 09:40', 'balance_check_month_end', 'Checked balance',                     0, 1),
 ('C003', '2026-09-26 09:05', 'balance_check_month_end', 'Checked balance',                     1, 0),
 ('C003', '2026-09-27 10:00', 'balance_check_month_end', 'Checked balance',                     1, 0),
 ('C003', '2026-09-28 09:20', 'balance_check_month_end', 'Checked balance',                     1, 0),
 ('C003', '2026-09-29 09:50', 'balance_check_month_end', 'Checked balance',                     1, 0),
 ('C003', '2026-09-22 10:30', 'renovation_simulator_abandoned', 'Stopped at step 2 of 4',       1, 0);

-- ===== Contextual data (micro-moments) ============================================
INSERT INTO context_events (customer_id, ts, event, detail, country, batch, released) VALUES
 ('C002', '2026-09-30 08:40', 'airport_abroad', 'Opened the KBC app at Narita International Airport, Tokyo', 'JP', 1, 0);
