# Sources

Frozen on 2026-11-09. This reproduces rendering from prepared monthly aggregates, not reconstruction of the raw case records. No individual records are included.

| Input | Source / attribution |
|:--|:--|
| Dengue + severe dengue, 2007–2021 | INS/SIVIGILA, [4hyg-wa9d](https://www.datos.gov.co/d/4hyg-wa9d), CC BY-SA 4.0 |
| Cases, 2022–2024 | INS/SIVIGILA, [wns8-p38i](https://www.datos.gov.co/d/wns8-p38i), CC BY 4.0 |
| Onset reconstruction: 2007, 2008, 2013; cases: 2025 | [INS public microdata](https://portalsivigila.ins.gov.co/Paginas/Buscador.aspx), downloaded 2026-11-06/07 |
| Population adjustment | [DANE municipal back-projections / projections](https://www.dane.gov.co/index.php/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion), CNPV 2018, post-COVID update |
| Municipalities and town centres | DANE MGN 2025 and [DIVIPOLA gdxc-w37w](https://www.datos.gov.co/d/gdxc-w37w); boundaries simplified 50 m |
| ONI, ERSSTv6 | [NOAA CPC](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/), public domain |
| Neighbouring countries | [Natural Earth](https://www.naturalearthdata.com/), public domain |

INS tables were downloaded 2026-11-06; preserve the source attribution and applicable licences when redistributing their derivatives. DANE and INS portal data remain subject to their publishers' terms. Font notices are in `fonts/`.

`data.gpkg`: municipal O/E (`oe_YYYYMM`), town-centre counts (`c_YYYYMM`), lagged ONI/phase, department outlines, neighbours. `timeline.csv` holds national counts and lagged ONI. Zero-case municipalities still exist; grey polygons mean expected cases < 2.

Weeks go to the month of their Wednesday. Expected cases = the municipality's pooled calendar-month rate per person-week, 2007–2025, × that year's population × weeks in the bin. Ratios are unrounded. In reconstructed years, out-of-year onsets are clipped to their INS year's boundary weeks; unreadable dates retain the supplied week. Mapiripana is merged into Barrancominas. Unusable occurrence codes are excluded.

ONI is centred three months before each map month. Phases use one-decimal rounding and five consecutive qualifying seasons. This is a retrospective display choice, not a validated delay or causal result. The baseline includes epidemic years and the displayed observation. Colours are not significance tests.
