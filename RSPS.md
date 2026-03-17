**CONSTRUCTION PROCESS**

**(Part 1) TOTALES - Overall Market Trend**

**What is the direction/trend of the overall market? (MTPI)**

You have already completed this step already - please copy your approved level 2 submission (MTPI) into the spreadsheet on “Tab 1 - TOTALES Trend”.

You will need to define the entry and exit criteria based on the TPI (not the indicators!). 

The recommended, most robust entry/exit criteria you should use is based on the STATE. 
Example: Entry = MTPI Score > 0.1 | Exit = MTPI Score < -0.1. Keep your thresholds symmetrical, and within reasonable limits. We do not recommend you use RoC, or strength for your entry/exit criteria. Save this experimentation once you know how to properly backtest your systems.

Do not overcomplicate this section, but remember the RSPS is a long-only strategy, and your RSPS construction should reflect this. 

**(Part 2) ETHBTC / SOLETH^ / SOLBTC^ - Conservative Trend (Mini TPI’s)**
^These TPI’s are optional. 

**How much should we allocate to each major?**

For this part, you will be required to construct your medium term TPI’s on the ETHBTC chart. 
If you have opted to include SOL in your conservative trend, you need to do this for the SOLETH and SOLBTC ratios also.

The tickers you **MUST** use for your analysis are: 
>ETHBTC - (BINANCE:ETHBTC)
>SOLETH - (BINANCE:SOLETH)
>SOLBTC - (BINANCE:SOLBTC)

(These are the tickers with the most price history).

These TPI(s) will assist you in determining which majors will outperform the others. 

For example, If ETH is outperforming BTC then the ETHBTC ratio will increase, and if BTC outperforms ETH the time-series will decrease. The same is true for the other ratios. 

**PLEASE NOTE: The ratios are INDEPENDENT of the overall market trend.**

You will need to build your mini medium term TPI’s to carry out trend analysis on the ratios. 

If you **ARE NOT** including SOL in the conservative trend, you will need to build 1 TPI for this section, and carry out trend analysis on the **ETHBTC** ratio. 
>If ratio is >0, you will hold more ETH in the Conservative Portfolio (80% ETH, 20% BTC)
>If ratio is <0, you will hold more BTC in the Conservative Portfolio (20% ETH, 80% BTC)

If you **ARE** including SOL in the conservative trend, you will need to build 3 TPI’s for this section, and carry out trend analysis on the **ETHBTC, SOLETH** and **SOLBTC** ratios. 

If you chose 100% to the dominant major, here is an example of how you would allocate to each asset: (Say, the ETHBTC ratio is >0, the SOLETH ratio <0 and the SOLBTC ratio is <0)
>Rank #1 = ETH, and thus you would allocate (100%)
>Rank #2 = BTC, and thus you would allocate (0%)
>Rank #3 = SOL, and thus you would allocate (0%)

If you chose 80% / 20% to the dominant major, here is an example of how you would allocate to each asset: (Say, the ETHBTC ratio is <0, the SOLETH ratio >0 and the SOLBTC ratio is >0)
>Rank #1 = SOL, and thus you would allocate (80%)
>Rank #2 = BTC, and thus you would allocate (20%)
>Rank #3 = ETH, and thus you would allocate (0%)

Remember that the more assets you include will exponentially increase the complexity of the system; so beware of including too many tokens as this will increase the workload (updating the system and maintenance) and render the system unusable. 

**PLEASE NOTE:** In the original summit presentation, the allocation weight was calculated as a function of strength of the TPI instead of its “state” (<> 0).
This was later revised, as it was the incorrect application of the TPI.

You are required to use at least **5 (FIVE)** indicators for your ratio TPI’s. There is no limit, but remember quality > quantity. 

You are also required to use **AT LEAST** 1 perpetual or oscillator in your TPI. For example, 4 perpetuals & 1 oscillator is fine. 

Finally you are **NOT ALLOWED** to use more than two indicators from the same publisher or creator per TPI. This will ensure you discover high-quality indicators and avoid over-reliance on a single author.

**(Part 3) OTHERS.D - Trash Trend**

**How much of the portfolio should be allocated in altcoins?**

In this section, you are measuring the probability of altcoins (excluding the top 10 coins in market cap) outperforming majors and which will tell you how much of your portfolio you should allocate to altcoins.

The ticker you **MUST** use for your analysis is:
>CRYPTOCAP:OTHERS.D 

This is a measure of altcoin dominance. NOT TO BE CONFUSED WITH **OTHERS**. 

You are required to build a mini medium term TPI to carry out trend analysis on OTHERS.D. 

You are permitted to change the max allowed allocation to altcoins. This should be aligned with your risk appetite, but we **DO NOT** recommend exceeding 20%. (Remember the barbell portfolio principle). 

You are required to use at least **5 (FIVE)** indicators for your OTHERS.D TPI. There is no limit, but remember quality > quantity. 

You are required to use **AT LEAST** 1 perpetual or oscillator in your TPI. For example, 4 perpetual & 1 oscillator is fine. 

You are **NOT ALLOWED** to use more than two indicators from the same publisher or creator. This will ensure you discover high-quality indicators and avoid over-reliance on a single author.

**(Part 4) ALTCOINS - Trash Tournament**

**For our trash portfolio, which tokens should we allocate capital to?**

This section has been changed significantly since the summit ratio portfolio presentation to better reflect the core applications of the TPI. 

Recall from the TPI signal lesson how the 3 derivatives of the TPI were discussed: 
>State
>RoC
>Strength
⠀
If we allocate to the trash as a function of strength, we run the risk that allocations will be at their largest during turning points. Therefore the allocations will no longer be made as a function of strength, but as a ‘state’ based tournament style system.

The goal of the trash tournament is to quantitatively determine the strongest coins from a list at any given time. This is determined by sequentially filtering tokens using pre-defined criteria, summing the result and allocating to the highest scoring tokens. 

You are permitted to change the sheet template if you wish, provided you ensure all formula functionality is retained. If you are not proficient with google sheets and formulas, we do not recommend you do this. 

Here is a rough outline of what you need to do to build your own. Please note, these steps are not “prescriptive”, and we encourage innovation in this section. You should design your trash table to suit your preferences and investing style. 

**Step 1 - Token Selection:**
Form a list of tokens you would like to include in your trash token tournament. Remember to keep mind the biases listed in the conceptual foundations. You are required to include **AT LEAST 15.**

**Step 2 - Criteria Development:**
This is the crux of the trash tournament. You need to develop a set of criteria (we call them filters) that award tokens points when they show the desired behaviour. 

For example, you might decide that one of your filters will be **(Token Trend / USD)**, so what you will do is go through each of your tokens, and award a 1 to tokens which exhibit the desired behaviour (uptrend) and a 0 to tokens that do not (downtrend). You then will repeat this process for the other filters, assigning a score of 1 or 0 for each. 

Some examples of filters include, but are not limited to: 
>(Token Trend / USD) 
>(Token Trend / BTC/ETH)
>(Token beta > median beta of all tokens)^
>(Token market cap < median market cap of all tokens)^

^*Has a slightly different way of scoring - read “Step 3 - Scoring” below.*

You are required to have a **MINIMUM of 5 quantitative filters** in your table. We welcome innovation in this section provided it makes sense.
**EVERY FILTER** must come with a thesis answering questions such as:
>Why did you choose this filter?
>How does it add an edge to your system?
>What outcome are you expecting?
 These are just examples, you’re encouraged to innovate and go deeper. The more thought, the better.

For each filter, please make sure to: 
>Write down the indicators and settings you used. 
>Use a diverse range of indicators for your ratio filters; do not use the same indicator for all filters.
>Avoid using basic indicators like an EMA crossover or Aroon. 

**Step 3 - Scoring**

For ratio filter scoring, use 1 (Uptrend) or 0 (Downtrend). Do not use -1. 

If you include filters with metrics that are a continuum of numbers (i.e. Market Cap, Beta Scores etc.) then use a formula to define a “winning tally” (1 or 0) to the token if it exhibits the desired behaviour (<> median is common, but feel free to innovate). 

————————————————————————————————————

**Step 4 - Further Considerations**

**Preliminary Filters:** 
You may consider including preliminary filters in your trash table. (ie. 1 important filter that may instantly disqualify a token from proceeding further in the tournament). This is valid, provided the filter used is important and makes sense. 

Example: Using beta or market cap as preliminary filters **IS NOT** acceptable, as this will immediately disqualify half of your tokens from your table, and they are not not overly important and should be treated more as a complementary filter. 

An example of a filter **THAT IS** acceptable is (Token Trend / USD). After all, why should we have the potential to allocate to a token at all if it is in a downtrend… 

**Prohibited Filters:** 
>Distance from ATH. 
>Sharpe, sortino or omega ratios. 
>Other mean reverting filters. 
>Anything qualitative. 
>Holder distribution.^

*^If this sort of thing is a concern for you, simply do not include tokens that do not meet this criteria in the table in the first place.*

**Tiebreaker Criteria:** 
If you have too many tokens which pass all of your filters, you can include an ALT / ALT matrix; where you perform trend analysis of each winning alt to each other winning alt. See example below. 

======| Token A | Token B | Token C
Token A |      x      |      0      |      0
Token B |      1      |      x      |      0
Token C |      1      |      1      |      x

You can see here that token C is the strongest token. You may choose to only allocate capital to token C, or you might choose the top two. (Token C and Token B). 

The winning tokens will all go in the ‘small cap’ holding section of the portfolio. Allocations between individual tokens must be **EQUAL**, and they can have no individual adjustable weights. If you have 4 tokens, each will comprise 25% of the trash component of the portfolio. 

The table is already set up to split the alt allocations even for you. The only change you are allowed to make is the 3.99 of minimum score to something higher based on the number of filters you use.

You are to use the spreadsheet tab (4 - Small Trend) for this part. 

The content of this tab is only for your reference and we **REQUIRE** you to be creative in developing your own trash selection in line with the methods listed above.

**SUBMISSION AND GRADING**

**Here is EXACTLY what you need to submit:**
Failure to follow these strict guidelines will result in automatic failure of your submission.

**What we will grade:** 

**Part 1 (TOTALES)**
Include your Level 2 **APPROVED** TPI into the RSPS Portfolio spreadsheet in tab ‘(1 - TOTALES Trend)’ and provide a detailed description of the criteria used to enter or exit a position. The date that you need to form the analysis and a portfolio is 23 February 2024. 

**Part 2 & 3 (CONSERVATIVE TREND TPI’S, OTHERS.D TPI)**
Provide time coherent TPI’s on the tickers with the proposed allocations. 
The date that you need to form the analysis and a portfolio is 23 February 2024. 

**Each** TPI should be accompanied by: 
>A time coherency summary. (The time coherency summary is a screenshot which contains the marked signals for **ALL** indicators along with your ISP. No indicators). 
>A screenshot of **JUST** your intended signal period. 
>Individual screenshots for each indicator, overlaid with your intended signal period and the signals for that specific indicator marked. Ensure that your signals are marked **CORRECTLY** in alignment with the method shown in the “Realistic Entries and Exits Guide”, which can be found in the community guides and helpful posts document.
>If an indicator spits out a neutral signal, it simply inherits the direction of the previous one, and must be treated as such in your screenshots.

**Part 4 (TRASH TOURNAMENT TABLE)**
Provide a trash tournament which selects tokens for your trash portfolio in accordance with the guidelines.
The date that you need to form the alts analysis and a portfolio is 23 February 2024.
No screenshots are required for this part. 