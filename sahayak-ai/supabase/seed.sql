-- ===========================================================================
-- Sahayak AI — welfare scheme seed data
-- NOTE: scheme_vector_embedding is intentionally left NULL here. Generate real
-- 1536-dim embeddings with text-embedding-3-small at deploy time, e.g. run
-- backend/scripts/seed_embeddings.py (or an equivalent edge function) which
-- reads these rows, embeds `description`, and UPDATEs scheme_vector_embedding.
-- The `eligibility_rules` JSONB mirrors backend/app/data/seed.py exactly.
-- ===========================================================================

INSERT INTO welfare_schemes (title, description, eligibility_criteria_summary, category, eligibility_rules)
VALUES
(
  'Rashtriya Arogya Nidhi (RAN)',
  'Financial assistance to patients living below the poverty line who are suffering from major life-threatening diseases such as cancer, kidney failure, and heart conditions, to receive treatment at government hospitals.',
  'BPL households; life-threatening illness (cancer, renal, cardiac); treatment at government / recognised hospital.',
  'Medical',
  '{"max_income":150000,"medical_keywords":["cancer","carcinoma","tumor","malignant","renal","kidney","dialysis","cardiac","heart","transplant","leukemia"]}'
),
(
  'Ayushman Bharat PM-JAY',
  'Provides health cover of up to five lakh rupees per family per year for secondary and tertiary care hospitalisation to poor and vulnerable families across India.',
  'Economically weaker families; covers hospitalisation for a wide range of medical and surgical conditions.',
  'Medical',
  '{"max_income":250000,"medical_keywords":["cancer","renal","kidney","dialysis","surgery","cardiac","chemotherapy","hospitalisation","carcinoma","chronic"]}'
),
(
  'Pradhan Mantri National Dialysis Programme',
  'Free dialysis services for poor patients suffering from chronic kidney disease and end-stage renal failure at district hospitals.',
  'Chronic kidney disease / renal failure patients requiring dialysis; priority to low-income households.',
  'Medical',
  '{"max_income":200000,"medical_keywords":["kidney","renal","dialysis","nephrology","ckd"]}'
),
(
  'National Family Benefit Scheme (NFBS)',
  'A one-time lump-sum family benefit to below-poverty-line households upon the death of the primary breadwinner, supporting bereaved families including widows and dependent children.',
  'BPL family; death of primary breadwinner; one-time relief grant.',
  'Social Security',
  '{"max_income":100000,"keywords":["widow","family","breadwinner"]}'
),
(
  'Post-Matric Scholarship (SC/ST/OBC)',
  'Scholarships for students from scheduled castes, tribes and other backward classes studying at post-matriculation levels to cover tuition and maintenance, reducing school and college dropout.',
  'Students in classes 11+ / college; family income under 2.5 lakh; covers tuition and maintenance allowance.',
  'Education',
  '{"min_age":13,"max_age":25,"max_income":250000,"keywords":["scholarship","student","school","college","education"]}'
),
(
  'Pre-Matric Scholarship',
  'Financial support for school-going children up to class 10 from economically weaker sections to cover books, uniforms and fees.',
  'School children up to class 10; low-income family; covers books and fees.',
  'Education',
  '{"min_age":5,"max_age":16,"max_income":200000,"keywords":["scholarship","student","school","education","child"]}'
),
(
  'Indira Gandhi National Disability Pension Scheme',
  'Monthly pension to persons with severe or multiple disabilities from below-poverty-line households to support their livelihood and care.',
  'Age 18-79; severe disability (40%+); BPL household.',
  'Pension',
  '{"min_age":18,"max_age":79,"max_income":100000,"requires_disability":true,"medical_keywords":["disability","disabled","locomotor","blind"]}'
),
(
  'Indira Gandhi National Old Age Pension Scheme',
  'Monthly old-age pension for senior citizens aged sixty years and above belonging to below-poverty-line families.',
  'Age 60+; below-poverty-line household.',
  'Pension',
  '{"min_age":60,"max_income":100000,"keywords":["senior","elderly"]}'
),
(
  'Indira Gandhi National Widow Pension Scheme',
  'Monthly pension to widows aged forty to fifty-nine years from below-poverty-line households to provide social security.',
  'Widows aged 40-59; BPL household.',
  'Pension',
  '{"min_age":40,"max_age":59,"max_income":100000,"gender":"Female","keywords":["widow"]}'
),
(
  'Chief Minister''s Relief Fund (Medical Aid)',
  'Discretionary state medical and disaster relief assistance for citizens facing acute financial distress from illness or emergencies not fully covered by other central schemes. A general-purpose safety net.',
  'Any resident in acute distress; general medical / emergency relief.',
  'Medical',
  '{"max_income":300000,"is_fallback":true}'
);
