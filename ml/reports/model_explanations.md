# Learned model feature associations

Selected model: linear_svm. These weights are learned associations, not causes. Local contributions multiply these weights by the input TF-IDF values. SVM margins are not probabilities.

## aggregation

Training positives: 220; intercept: -0.908809; validation F1: 0.8235; test F1: 0.6869.

Positive weights: sum (2.3117), group by (2.1964), aggregate (2.0388), group (2.0265), by (1.5139), max (1.2457), 2023 (1.2059), aggregate function (1.1712), count (1.0996), 2022 (0.9815), avg (0.9569), select (0.9547), array_agg (0.8921), over (0.8630), 300 (0.7796)

Negative weights: 2026 (-0.9519), pandas (-0.8775), 2025 (-0.8068), dataframe (-0.7122), df (-0.7052), index (-0.6763), tables (-0.6371), time (-0.5331), a (-0.5237), 1 group (-0.4862), code (-0.4839), match (-0.4807), new (-0.4711), import (-0.4695), 2024 (-0.4595)

## async

Training positives: 63; intercept: -1.003929; validation F1: 0.9600; test F1: 0.8276.

Positive weights: async (1.8728), await (1.8178), async function (1.1104), promise (1.0485), console.log (1.0118), async await (0.9581), resolve (0.8538), an async (0.7574), asynchronous (0.7219), wait (0.6692), to wait (0.6383), function (0.6366), settimeout (0.5859), catch (0.5780), new promise (0.5755)

Negative weights: async def (-0.5146), import (-0.4530), def (-0.4469), script (-0.3607), python (-0.3540), with (-0.2793), p (-0.2591), response.status (-0.2557), component (-0.2502), print (-0.2487), asyncio (-0.2439), synchronous (-0.2374), select (-0.2348), asyncio.run (-0.2314), doesn (-0.2301)

## javascript

Training positives: 436; intercept: -0.504995; validation F1: 0.8543; test F1: 0.8173.

Positive weights: javascript (3.0421), const (2.6444), let (1.8258), console.log (1.6144), js (1.3689), script (1.3370), function (1.2601), page (1.2117), html (1.2003), node.js (1.0201), await (0.9935), browser (0.9746), var (0.9501), click (0.9043), node (0.8987)

Negative weights: python (-1.6499), def (-1.5721), sql (-1.1582), import (-1.1267), table (-1.1133), select (-1.0962), pandas (-0.9640), print (-0.9583), column (-0.8778), join (-0.7989), dataframe (-0.7802), from (-0.7555), columns (-0.7329), async def (-0.6961), 1 (-0.6751)

## joins

Training positives: 169; intercept: -0.929078; validation F1: 0.6957; test F1: 0.6667.

Positive weights: join (3.7019), tables (2.2626), table (1.2411), 2024 (1.1473), to join (1.0141), two tables (0.9867), join i (0.8727), rows (0.8212), match (0.7730), records (0.7690), 2 tables (0.7360), mysql (0.6787), query (0.6767), left join (0.6555), clause (0.6492)

Negative weights: 2026 (-0.5773), group (-0.5341), into (-0.5181), sum (-0.4738), oracle (-0.4730), python (-0.4721), schema (-0.4617), dataframe (-0.4525), event_id (-0.4474), pandas (-0.4390), 3 4 (-0.4295), year (-0.4238), dataframes (-0.4101), should (-0.4006), long (-0.3993)

## pandas

Training positives: 302; intercept: -0.831160; validation F1: 0.9343; test F1: 0.9242.

Positive weights: pandas (5.1690), dataframe (3.0812), df (2.9078), pd.dataframe (1.4851), nan (1.2969), a dataframe (1.2173), series (1.2149), import pandas (1.1761), pd (1.1756), data (1.1246), column (1.1115), pandas as (1.1039), as pd (1.0953), index (1.0569), dataframes (1.0526)

Negative weights: select (-1.0010), query (-0.8483), table (-0.8014), sql (-0.6838), const (-0.6066), a table (-0.5234), id (-0.4898), null (-0.4813), result (-0.4638), react (-0.4514), text (-0.4335), by (-0.4323), pyspark (-0.4067), width (-0.4037), from (-0.4003)

## python

Training positives: 625; intercept: -0.260961; validation F1: 0.9524; test F1: 0.9481.

Positive weights: python (3.8565), def (2.7579), pandas (2.7145), dataframe (2.3839), import (2.2434), print (2.1836), df (1.4078), str (1.3778), none (1.2429), in python (1.2006), self (1.0938), flask (0.9726), a dataframe (0.9318), f (0.8790), dataframes (0.8749)

Negative weights: const (-2.0963), table (-1.7602), select (-1.6861), react (-1.6653), query (-1.4172), let (-1.4152), sql (-1.3600), javascript (-1.2739), null (-1.0666), console.log (-1.0000), div (-0.8584), component (-0.8483), by (-0.7930), function (-0.7453), group by (-0.7333)

## react

Training positives: 290; intercept: -0.652592; validation F1: 0.9683; test F1: 0.8855.

Positive weights: react (4.9335), component (1.7792), const (1.6664), in react (1.4726), usestate (1.4170), useeffect (1.3995), classname (1.2277), export (1.1913), next.js (1.1313), a react (1.0207), app (0.9081), from react (0.8799), components (0.8432), onclick (0.8063), tailwind (0.8055)

Negative weights: script (-0.9043), class (-0.8984), javascript (-0.6690), sql (-0.6467), python (-0.5986), def (-0.5511), print (-0.5162), pandas (-0.4608), id (-0.4575), table (-0.4531), template (-0.4471), all (-0.4364), column (-0.4346), body (-0.4313), div id (-0.4299)

## sql

Training positives: 661; intercept: -0.422084; validation F1: 0.9574; test F1: 0.9606.

Positive weights: table (3.0546), select (3.0059), sql (2.9645), query (2.3027), join (1.3798), by (1.3506), tables (1.2846), null (1.2428), postgresql (1.2305), where (1.1104), from (1.1040), a table (1.0890), mysql (1.0100), order by (0.9843), queries (0.9517)

Negative weights: pandas (-1.9426), dataframe (-1.6375), import (-1.4071), df (-1.2874), react (-1.2435), python (-1.2214), true (-1.1804), const (-1.1287), javascript (-0.9488), def (-0.9219), dataframes (-0.7898), index (-0.7485), code (-0.7426), a dataframe (-0.7247), print (-0.7244)
