Analyzing the Correlation Between Influencer Activity and Market Sentiment for Specific Tickers
I. Introduction
The proliferation of social media platforms has fundamentally altered the landscape of financial information dissemination and investor behavior.1 Individual investors increasingly rely on online communities and influential figures for market insights and trading ideas.3 This dynamic raises a critical question for market participants and analysts: to what extent does the activity of specific online influencers impact the sentiment surrounding a particular stock (ticker)? Understanding this relationship can provide valuable insights for investment strategies, risk management, and market analysis.1
This report provides a comprehensive analysis framework for investigating the correlation between influencer activity and market sentiment for a chosen ticker. It begins by detailing the application of Pearson correlation analysis, a standard statistical technique, outlining its methodology, assumptions, implementation steps, and inherent limitations, particularly the critical distinction between correlation and causation. Recognizing the constraints of Pearson's method, the report then explores alternative analytical approaches, including Granger causality testing, regression modeling, and event study methodology, evaluating their suitability for uncovering predictive relationships, isolating effects, and analyzing specific influence events.
Furthermore, this report offers a practical guide to constructing a data acquisition pipeline (or "data miner") necessary for such analyses. This includes defining data requirements, identifying primary data sources (social media platforms, news feeds), comparing data acquisition techniques (API integration vs. web scraping with relevant Python libraries), implementing sentiment analysis, performing essential data preprocessing and alignment, and considering appropriate database solutions for storing time-series data.
Finally, the report examines the landscape of market sentiment data sourcing, contrasting freely available indicators and APIs with paid institutional data providers. It evaluates the features, costs, and limitations of various options, providing guidance on selecting appropriate data sources based on analytical needs and resource constraints. The report concludes with strategic recommendations for conducting a robust and insightful analysis of the influencer-sentiment nexus in financial markets.
II. Pearson Correlation Analysis: Measuring Linear Association
The Pearson product-moment correlation coefficient, commonly denoted as r, is a widely used statistical measure to quantify the strength and direction of a linear relationship between two continuous variables.7 In the context of this analysis, it can be employed to assess the degree to which a chosen metric of influencer activity is linearly associated with a measured sentiment score for a specific stock ticker over a defined period.
A. Understanding Pearson's r
The coefficient r ranges from -1 to +1 8:
A value close to +1 indicates a strong positive linear correlation: as the influencer activity metric increases, the sentiment score tends to increase linearly.9
A value close to -1 indicates a strong negative linear correlation: as the influencer activity metric increases, the sentiment score tends to decrease linearly.9
A value close to 0 suggests little to no linear correlation between the two variables.9
The magnitude of r indicates the strength of the linear association, often interpreted using guidelines such as Evans (1996):.00-.19 (very weak),.20-.39 (weak),.40-.59 (moderate),.60-.79 (strong),.80-1.0 (very strong).10 It's crucial to note that Pearson's r is unitless and symmetric, meaning the correlation between variable X and Y is the same as between Y and X.8
B. Critical Assumptions
The validity of Pearson's r hinges on several key assumptions about the data 7:
Level of Measurement: Both variables (influencer activity metric and sentiment score) must be measured on an interval or ratio scale (i.e., continuous).7
Linearity: The relationship between the two variables should be approximately linear. This can be visually assessed using a scatterplot, where the data points should roughly form a straight line, not a curve.7
Normality: Data for both variables should ideally follow a normal distribution (bivariate normality is the formal assumption, often checked by examining individual variable normality).10 Pearson's r is sensitive to skewed distributions.10
Absence of Outliers: Significant outliers in either variable can disproportionately influence the correlation coefficient, potentially strengthening or weakening the perceived relationship misleadingly.7 Outliers might be identified as values exceeding a certain number of standard deviations from the mean (e.g., > 3.29).7
Independence of Cases: Each pair of observations should be independent of other pairs.8 This assumption is often violated in time-series data where observations at one point in time can be related to previous observations (autocorrelation).
Homoscedasticity: The variability of residuals (the difference between observed and predicted values) should be consistent across all levels of the independent variable. A scatterplot of residuals should appear roughly rectangular.8
Meeting these assumptions is paramount for a reliable interpretation of Pearson's r. However, financial data (like stock returns, which might indirectly relate to sentiment) and sentiment scores derived from social media are frequently characterized by non-normality (skewness, heavy tails), outliers (market crashes, viral posts, sudden news), potential non-linear relationships, and inherent time dependencies (autocorrelation). Applying Pearson correlation naively without rigorously checking and addressing these potential violations—through data transformations, outlier treatment, or selecting more robust statistical methods—can lead to spurious or misleading conclusions about the relationship's true nature and strength.
C. Steps for Performing Pearson Correlation Analysis
Define Variables: Clearly operationalize and quantify:
Influencer Activity Metric: Choose a specific, measurable metric (e.g., daily posts by the influencer mentioning the ticker, daily sum of likes/retweets on relevant posts, sentiment score of the influencer's own posts).
Sentiment Score: Choose a method for calculating aggregate sentiment for the ticker (e.g., daily average polarity score from all relevant posts, daily net sentiment difference, daily volume of positive/negative posts).6 The choice of these metrics is subjective and different choices can lead to different correlation results, impacting the final interpretation.
Data Collection: Gather time-series data for both variables and the corresponding stock ticker data (e.g., price, volume) for the desired period. (See Section IV for data acquisition details).
Data Preprocessing and Alignment:
Clean the data: Handle missing values, remove duplicates or noise.15
Time Alignment: Ensure both time series (influencer activity, sentiment score) are aggregated to the same frequency (e.g., daily, hourly) and aligned by timestamp. This is crucial for meaningful comparison.5 Pandas library in Python is typically used for this.16
Assumption Checking:
Visualize the relationship using a scatterplot to check for linearity and obvious outliers.9
Check for normality using histograms, Q-Q plots, or statistical tests (e.g., Shapiro-Wilk, Kolmogorov-Smirnov). Check skewness coefficients.10
Identify and consider handling outliers if they unduly influence the results.7
Address potential non-stationarity or autocorrelation if necessary, especially if moving towards time-series specific methods.
Calculation: Use statistical software or libraries (like SciPy in Python) to compute Pearson's r and its associated p-value.
Python Example Structure (using SciPy):
Python
from scipy.stats import pearsonr
import pandas as pd

# Assume df is a pandas DataFrame with columns:
# 'timestamp', 'influencer_metric', 'sentiment_score'
# Ensure data is properly aligned and preprocessed (Step 3)

# Perform Assumption Checks (Step 4)
# e.g., scatter plot: df.plot.scatter(x='influencer_metric', y='sentiment_score')
# e.g., normality tests...

# Handle outliers if necessary...

# Calculate Pearson correlation
# Ensure no NaN values in the columns being correlated
df_cleaned = df[['influencer_metric', 'sentiment_score']].dropna()

if not df_cleaned.empty and len(df_cleaned) > 1:
    correlation, p_value = pearsonr(df_cleaned['influencer_metric'], df_cleaned['sentiment_score'])
    print(f"Pearson correlation coefficient (r): {correlation:.4f}")
    print(f"P-value: {p_value:.4f}")

    # Interpretation based on r and p-value
    alpha = 0.05
    if p_value < alpha:
        print("The correlation is statistically significant (reject H0).")
    else:
        print("The correlation is not statistically significant (fail to reject H0).")
else:
    print("Insufficient data for correlation calculation after cleaning.")


5
Interpretation:
Evaluate the correlation coefficient (r) for strength and direction based on established guidelines.9
Assess the p-value. A statistically significant p-value (typically p<0.05) suggests that the observed correlation is unlikely to have occurred by random chance, providing evidence against the null hypothesis of zero correlation in the population (H0​:ρ=0).5 Studies applying this to sentiment and stock prices have found varying results, sometimes low or insignificant correlations 13, other times moderate negative correlations.5
Report the findings clearly, stating the r value, p-value, sample size, and explicitly mentioning the assumptions made and any potential limitations or violations encountered.10
D. Beyond Correlation: The Causation Caveat
A fundamental limitation of Pearson correlation is that it does not imply causation.10 A significant correlation between influencer activity and sentiment score does not prove that the influencer's actions caused the change in sentiment. Several possibilities exist:
Influencer Causes Sentiment: The influencer's posts directly influence public opinion.
Sentiment Causes Influencer Activity: The influencer reacts to existing sentiment trends, posting more when sentiment is already moving.
Confounding Variable: Both influencer activity and sentiment are driven by an unobserved third factor, such as a major news event, underlying company performance change, or broader market shift.20
Coincidence: The correlation might be spurious, especially if assumptions are violated or the timeframe is short.
Pearson's r only measures the degree of linear association; it provides no information about the underlying mechanism, directionality, or causal structure of the relationship.8 While calculating the coefficient using libraries like SciPy is computationally straightforward 5, the true analytical challenge and value lie in the meticulous data preparation, rigorous assumption validation, and cautious interpretation of the results, always bearing in mind the critical distinction between correlation and causation. Overlooking these aspects can render the calculated r value meaningless or, worse, lead to incorrect inferences about market dynamics.
III. Exploring Alternative Analytical Methods
While Pearson correlation provides a basic measure of linear association, its limitations—particularly its inability to infer causality or handle non-linearities—necessitate exploring alternative methods for a deeper understanding of the relationship between influencer activity and market sentiment. These alternatives can offer insights into predictive power, isolate effects while controlling for other factors, and analyze the impact of specific events.
A. Granger Causality: Testing for Predictive Power
Concept: The Granger causality test assesses whether past values of one time series (e.g., influencer activity) contain statistically significant information that helps predict future values of another time series (e.g., sentiment score), beyond the information already contained in the second time series' own past values.20 It originated in econometrics and tests for predictive causality based on temporal precedence: the "cause" must happen before the "effect" and contain unique predictive information.20 It's important to stress that Granger causality indicates predictive usefulness, not necessarily true causal mechanisms in a philosophical or scientific sense.20
Methodology: The test typically involves fitting and comparing vector autoregressive (VAR) models.20 A restricted model predicts variable Y using only its own past (lagged) values. An unrestricted model predicts Y using past values of both Y and variable X. An F-test or Chi-squared test evaluates whether the coefficients associated with X's lagged values in the unrestricted model are jointly statistically significant.20 A significant result implies that X "Granger-causes" Y. Key prerequisites include stationary time series data; non-stationary data must be differenced before testing.20 Selecting the appropriate number of lags is also crucial and can impact results.21
Application in Finance/Sentiment: Granger causality is frequently used in financial research to examine lead-lag relationships, such as whether sentiment (from news or social media) predicts stock returns or volatility, or vice versa.5 For instance, studies have applied it to test if Twitter sentiment Granger-causes stock returns 19 or if social media sentiment Granger-causes stock market movements.26 Some research found significant Granger causality even when Pearson correlation was low, suggesting predictive power might exist without strong linear association.19 Other studies reported statistically significant Granger causality from Twitter sentiment to stock prices.5
Limitations:
Not True Causality: As mentioned, it only tests for predictive ability based on past information.20
Omitted Variable Bias: If both X and Y are driven by a third, unmeasured variable with different lags, the test might incorrectly suggest causality between X and Y.20
Linearity Assumption: Standard Granger tests assume linear relationships, although non-linear extensions exist.
Stationarity Requirement: Data must be stationary or made stationary through differencing, which can sometimes obscure long-run relationships.20
Lag Selection: Results can be sensitive to the number of lags chosen.21
Misinterpretation: A common pitfall is interpreting Granger causality as proof of a direct causal link.22
B. Regression Models: Quantifying and Isolating Impact
Concept: Regression analysis models a dependent variable (e.g., sentiment score) as a function of one or more independent (predictor) variables (e.g., influencer activity metric, overall market sentiment, news volume, stock volatility). This allows analysts to estimate the magnitude and statistical significance of each predictor's effect on the dependent variable while potentially controlling for the influence of other relevant factors.3
Types and Methodology:
Linear Regression: The simplest form, assuming a linear relationship: Y=β0​+β1​X1​+β2​X2​+...+ϵ. The coefficients (β) estimate the change in Y for a one-unit change in X, holding other variables constant.6 Statistical tests determine if coefficients are significantly different from zero.
Panel Data Models: If analyzing data across multiple stocks or influencers over time, panel models (like Fixed Effects or Random Effects) can control for unobserved heterogeneity specific to each entity (stock/influencer) or time period, providing more robust estimates.4
Panel Quantile Regression (PQR): Extends regression to model the impact of predictors across different quantiles (e.g., median, 10th percentile, 90th percentile) of the dependent variable's distribution. This is useful for understanding if an influencer's impact differs in high-sentiment vs. low-sentiment environments, or during bull vs. bear markets.3
Application in Finance/Sentiment: Regression is widely used to study the impact of social media sentiment or activity on stock returns, volume, or volatility.3 For example, researchers might regress daily sentiment change on lagged influencer post frequency, controlling for market return and news volume. Studies have used linear regression to assess the impact of social media indicators on return rates 6 or employed panel models to examine the association between platform mentions (like WallStreetBets) and stock price/volume changes.4 PQR has been used to show how social media influence might intensify during bull markets or periods of high trading volume.3
Limitations:
Assumptions: Similar to Pearson correlation, linear regression relies on assumptions like linearity, independence of errors, homoscedasticity (constant variance of errors), and normality of errors. Violations can lead to biased or inefficient estimates.
Model Specification: The validity of results depends on correctly specifying the model, including relevant variables and their functional form. Omitting important variables can lead to biased coefficient estimates.
Multicollinearity: If predictor variables are highly correlated with each other, it becomes difficult to disentangle their individual effects.
Causality: While regression can show association while controlling for other factors, it doesn't inherently prove causation. Correlation among predictors or the possibility of reverse causality remain concerns.
C. Event Study Methodology: Analyzing Impact of Specific Events
Concept: Event study methodology is designed to measure the impact of a specific, identifiable event on a particular variable (typically stock prices/returns, but applicable to sentiment scores) over a defined period surrounding the event.19 It isolates the effect of the event by comparing the actual outcome during the "event window" to an expected outcome estimated from a period before the event (the "estimation window") based on a model of "normal" behavior.28 The difference is termed the "abnormal" return or change.
Methodology:
Event Definition: Clearly identify the event(s) of interest (e.g., a specific influential tweet, a major announcement amplified by the influencer, a regulatory filing mentioned). Define the event date (t=0).
Window Definition: Define the estimation window (e.g., 120 days ending 30 days before the event) used to estimate normal behavior, and the event window (e.g., day -1 to day +1, or a longer period around the event) over which the impact is measured.
Normal Performance Model: Estimate the expected return (or sentiment) during the event window using a model fitted over the estimation window (e.g., market model relating stock return to market return, or a simple mean model for sentiment).
Abnormal Performance Calculation: Calculate the abnormal return/sentiment for each day in the event window: ARt​=ActualReturnt​−ExpectedReturnt​.
Aggregation and Testing: Aggregate abnormal returns/sentiments across the event window (e.g., Cumulative Abnormal Return/Sentiment - CAR/CAS) and across multiple events if applicable. Use statistical tests (e.g., t-tests) to determine if the average abnormal performance is significantly different from zero.28
Application in Finance/Sentiment: Event studies are standard in finance to assess market reactions to news like earnings announcements, M&A, etc..30 They can be adapted to measure the impact of social media events, such as spikes in Twitter volume/sentiment 19, specific posts by influential figures 2, or news disseminated via social media.29 One study used event study to link bullish sentiment posts on StockTwits to positive abnormal returns, especially for small-cap stocks.28 Another identified events as spikes in ESG-risk related social media messages and measured subsequent abnormal returns.31
Limitations:
Event Identification: Requires well-defined, discrete events. Less suitable for analyzing the impact of continuous, low-level influencer activity.
Model Dependence: Results can be sensitive to the choice of the normal performance model.
Confounding Events: Other significant events occurring within the event window can contaminate the results, making it hard to isolate the impact of the event of interest.
Anticipation Effects: If the market anticipates the event, some impact might occur before the defined event window.
Exogeneity Assumption: Assumes the event itself is not caused by the variable being measured (e.g., assumes the influencer's post wasn't triggered by an anticipated price move).
D. Comparison and Guidance on Method Selection








Method
Core Question Answered
Key Strengths
Key Weaknesses/Assumptions
Relevance to Influencer-Sentiment Link
Pearson Correlation
Is there a linear association between two variables?
Simple to calculate and interpret; measures strength/direction of linear link
Linearity, normality, no outliers, independence assumptions often violated; Does NOT imply causation 10
Provides a basic, initial assessment of linear co-movement between influencer activity and sentiment.
Granger Causality
Does past influencer activity help predict future sentiment?
Tests for predictive relationships based on time precedence
Sensitive to lags, stationarity required, omitted variables; Predictive, not mechanistic, causality 20
Useful for exploring potential lead-lag relationships and forecasting value.
Regression Analysis
How much does influencer activity impact sentiment, controlling for other factors?
Quantifies impact magnitude; allows controlling for confounders; flexible model types
Requires correct model specification; assumptions on errors; multicollinearity; still correlational 3
Estimates the isolated effect of the influencer, providing a more nuanced view than simple correlation.
Event Study
What is the short-term impact of a specific influencer action/event on sentiment?
Isolates impact of discrete events; widely used in finance
Requires clear events; sensitive to model/window choice; confounding events problematic 19
Ideal for measuring sentiment reaction to specific, significant posts or announcements by the influencer.

Guidance:
Begin with Pearson correlation (after careful assumption checks) for a preliminary understanding of the linear association.
If the goal is to determine if influencer activity has predictive value for future sentiment changes, use Granger causality.
To quantify the influencer's impact while accounting for other market variables (like overall market mood or news flow), employ regression analysis.
To analyze the immediate market or sentiment reaction to specific, significant influencer posts or announcements they amplify, use event study methodology.
Often, a combination of methods provides the most robust insights.26 For example, finding both significant Pearson correlation and Granger causality strengthens the evidence for a meaningful relationship. Using regression can help confirm if the correlation holds after controlling for other known drivers of sentiment.
Moving beyond simple correlation inevitably introduces greater complexity and new assumptions (e.g., stationarity for Granger, correct model specification for regression). There is no single "best" method; the choice must align with the specific research question, the nature of the available data, and the desired level of analytical depth. Academic research frequently employs multiple techniques, suggesting that relying on one test alone is often insufficient for drawing reliable conclusions in complex systems like financial markets influenced by social media.3 Furthermore, it's crucial to remain aware of the nuances of "causality." None of these standard methods definitively prove cause-and-effect in a mechanistic sense; they offer evidence of association, prediction, or impact under specific assumptions. Claims of causality should always be made cautiously, ideally supported by domain knowledge and potentially more advanced causal inference techniques.33
IV. Building Your Data Acquisition Pipeline (Data Miner)
Constructing a system to automatically collect, process, and store the necessary data—a data miner—is a critical prerequisite for analyzing the relationship between influencer activity and market sentiment. This involves careful planning of data requirements, selecting appropriate sources and acquisition techniques, implementing sentiment analysis, performing rigorous preprocessing, and choosing a suitable data storage solution.
A. Defining Data Requirements
Before building the pipeline, precisely define the data needed:
Influencer Activity:
Identify target influencer(s) by their unique identifiers on relevant platforms (e.g., X/Twitter handle, Reddit username, StockTwits profile).
Define the specific activity metric(s) to capture (e.g., count of posts mentioning the ticker per time unit, sentiment extracted specifically from the influencer's posts, engagement metrics like likes/retweets/comments on relevant posts).
Sentiment Metrics:
Define the scope: Sentiment from all posts mentioning the ticker on a platform, or only posts interacting with the influencer?
Define the calculation: How will sentiment be quantified and aggregated? (e.g., average polarity score per day/hour, volume or ratio of positive/negative posts per time unit). (See Sentiment Analysis Implementation below).
Stock Data:
Specify the ticker symbol(s).
Determine required data points (e.g., closing price, trading volume, open, high, low; potentially intraday data for higher frequency analysis).
Define the required frequency (daily, hourly, minute-by-minute).
Timeframe: Specify the historical start and end dates for the analysis.
B. Primary Data Sources
Social Media Platforms: X (formerly Twitter), Reddit, and StockTwits are commonly cited sources for financial sentiment and influencer activity.1 Consider other platforms if relevant to the specific influencer or ticker community (e.g., specialized forums, Discord servers).
Financial News Feeds: Include data from credible news sources to capture broader market context or identify confounding events that might influence both sentiment and influencer activity.13 Some data APIs provide integrated news feeds.14
C. Acquisition Techniques: APIs vs. Web Scraping
Data can primarily be acquired through official Application Programming Interfaces (APIs) or by web scraping.
1. API Integration: Using official APIs is generally preferred for reliability, structured data, and adherence to platform terms.
Platform APIs and Python Wrappers:
X/Twitter: Utilizes the X API v2. Access is tiered: Free (highly limited: 50 reads/month, 500 posts/month as of late 2024), Basic ($200/month for 10k reads/month), Pro ($5,000/month for 1M reads/month), and Enterprise (starts at $42,000+/year).40 The cost, especially for significant data volumes needed for robust analysis, presents a major barrier for individuals and smaller teams, representing a huge risk for developers building on the platform.40 The Python library Tweepy simplifies interaction with the X API, handling authentication, rate limits, and data parsing.42
Reddit: Offers an official API requiring app registration and adherence to rate limits. Direct API access to extensive historical data can be challenging. PRAW (Python Reddit API Wrapper) is the standard Python library for interacting with the Reddit API.45 Recent Reddit API changes have impacted third-party data archives like Pushshift, which were crucial for historical data collection, making this task more difficult.47 Libraries like PMAW attempt to facilitate bulk data retrieval via Pushshift using multithreading but depend on Pushshift's availability and functionality.48 Building and maintaining a personal Reddit archive is a complex alternative.49
StockTwits: Provides an official API that appears to offer free access with an API key, enabling access to data streams, messages, charts, and social graph information.50 It supports various SDKs, including Python, and seems more accessible for financial social data compared to X.50 Integration partnerships also exist, for instance, with brokerage API providers like Alpaca.52
Costs and Limitations: API terms, pricing, and rate limits change frequently, particularly for platforms like X.40 It is essential to consult the latest official documentation. Free tiers invariably impose strict limitations (on data volume, history, request frequency, commercial use) that may be insufficient for comprehensive or real-time analysis.39
2. Web Scraping: An alternative when APIs are too costly, restrictive, or lack necessary data (e.g., historical posts not available via API).
Python Libraries:
Requests, urllib3, httpx: Used to make HTTP requests and retrieve the raw HTML content of web pages. Suitable for static websites where content is present in the initial HTML source.54 httpx offers asynchronous capabilities.57
Beautiful Soup (BS4): A library specifically for parsing HTML and XML documents. It excels at navigating the document structure and extracting data from the HTML retrieved by libraries like Requests.54 Ideal for static pages.
Selenium, Playwright: Browser automation tools capable of controlling a web browser (like Chrome, Firefox) programmatically. They can render JavaScript, simulate user interactions (clicking, scrolling, filling forms), and thus scrape dynamic websites where content loads after the initial page request.54 Playwright is generally considered more modern, faster, and more feature-rich than Selenium.55
Scrapy: A comprehensive framework designed for building large-scale, efficient web crawlers and scrapers. It handles requests asynchronously, includes mechanisms for data processing (pipelines) and export, and is extensible. While powerful, it has a steeper learning curve than simpler libraries.54 It can be integrated with browser automation tools for JavaScript rendering.54
Web Scraping Considerations:
Legality/Ethics: Always check the website's robots.txt file and Terms of Service before scraping. Respect limitations and avoid overloading servers.
Technical Hurdles: Modern websites often employ anti-scraping measures (CAPTCHAs, IP blocking, user-agent checks, dynamic content loading, complex JavaScript, TLS fingerprinting 56). Bypassing these requires sophisticated techniques and constant adaptation.
Maintenance: Scrapers are brittle; they break whenever the target website's structure or design changes, requiring ongoing maintenance.
Performance: Browser automation tools (Selenium, Playwright) are significantly slower and more resource-intensive than direct HTTP requests.54
Table: Comparison of Python Web Scraping Libraries
Library
Primary Use
Handles Dynamic JS?
Ease of Use
Performance / Resource Use
Built-in Anti-Detection Features
Requests/httpx
Making HTTP requests
No
High
Fast / Low
No
Beautiful Soup
Parsing HTML/XML
No
High
Fast / Low
No
Selenium
Browser automation / Dyn. sites
Yes
Medium
Slow / High
Limited
Playwright
Browser automation / Dyn. sites
Yes
Medium
Moderate-Slow / High
Some (e.g., waits)
Scrapy
Large-scale scraping framework
Via integration
Low
Very Fast / Medium
Extensible via middleware

D. Implementing Sentiment Analysis
Once text data (e.g., posts mentioning the ticker) is collected, sentiment analysis is applied to quantify the emotional tone.
Techniques:
Lexicon-Based: Relies on dictionaries mapping words to sentiment scores (e.g., positive, negative, neutral). Examples include VADER.58 Strengths: Simple, fast. Weaknesses: Struggles with context, negation, sarcasm, domain-specific language.
Machine Learning-Based (Supervised): Involves training classification models (e.g., Naive Bayes, Support Vector Machines) on datasets where text samples have been pre-labeled with sentiment categories.58 Strengths: Can learn complex patterns beyond simple keywords. Weaknesses: Requires substantial labeled training data, performance depends heavily on training data quality and relevance.
Deep Learning-Based: Utilizes neural networks like Recurrent Neural Networks (RNNs) or Transformer models (e.g., BERT, GPT).61 Strengths: State-of-the-art performance, better understanding of context and nuance. Models like FinBERT are pre-trained specifically on financial text, potentially offering superior accuracy for financial sentiment analysis.63 Weaknesses: Computationally intensive, require significant data for training/fine-tuning, can be complex to implement.
Hybrid: Combines elements of lexicon/rule-based methods with machine learning approaches.61
Python Libraries:
NLTK: A foundational NLP library. Includes the VADER sentiment analysis tool, which is specifically tuned for social media text.17
TextBlob: Provides a simple interface for common NLP tasks, including sentiment analysis that returns polarity (ranging from -1 to +1) and subjectivity scores. Often used as a baseline.1
spaCy: An efficient library for building production-level NLP pipelines. While not having a built-in sentiment analyzer by default, it allows easy integration of custom or third-party sentiment components.58
Transformers (from Hugging Face): Offers access to a vast library of pre-trained deep learning models, including BERT, RoBERTa, GPT variants, and domain-specific models like FinBERT. Enables fine-tuning for specific sentiment analysis tasks.61
Generating Sentiment Scores: The chosen library/technique is applied to the collected text data. The output (e.g., polarity scores) must then be aggregated over consistent time intervals (e.g., daily average, hourly sum of positive/negative mentions) to create a time series suitable for correlation or other analyses.13 Scores might be rescaled (e.g., -100 to 100) for easier interpretation.13 Given the nuances of financial language (jargon, specific contexts, potential for manipulation), relying solely on general-purpose, off-the-shelf sentiment tools may be insufficient. Achieving accurate financial sentiment likely requires using domain-specific models (like FinBERT) or carefully customizing lexicon-based approaches or fine-tuning machine learning models on relevant financial text data.60
E. Essential Data Preprocessing and Alignment
Raw data collected from various sources is rarely ready for analysis. Rigorous preprocessing is crucial:
Time-Series Alignment: This is paramount. All data streams—influencer activity, sentiment scores, stock prices, volume—must be synchronized to the same temporal frequency (e.g., daily closing values, hourly averages) using timestamps. Tools like Python's Pandas library offer powerful functions (resample, merge_asof) for this task.5 Failure to align data correctly will invalidate any time-based analysis.
Data Cleaning: Address missing values using appropriate techniques (e.g., forward fill, interpolation, or deletion, considering the time-series nature).16 Remove duplicate entries. Filter out noise or irrelevant data points.15
Outlier Handling: Investigate outliers identified during assumption checks. Decide whether to remove, cap, or transform them based on their likely cause (data error vs. genuine extreme event).7
Stationarity Check (if needed): For methods like Granger causality, test time series for stationarity using statistical tests (e.g., Augmented Dickey-Fuller). If non-stationary, apply differencing (calculating the change between consecutive points) until stationarity is achieved.20
F. Storing Your Data: Database Considerations
Storing potentially large volumes of time-stamped data efficiently requires careful consideration of database technology. While standard relational databases can work for smaller datasets, specialized time-series databases (TSDBs) are often more performant and scalable for this type of data.
Why TSDBs? Time-series data (prices, sentiment scores over time) is characterized by time-stamped entries, high ingestion rates, and queries that are often time-centric (e.g., "average sentiment over the last 24 hours"). TSDBs are optimized for these characteristics.65
Leading Options:
TimescaleDB: An extension built on PostgreSQL, making it a relational TSDB. It uses standard SQL, allowing leverage of the vast PostgreSQL ecosystem and complex queries involving JOINs.65 It generally performs well with high-cardinality data (many unique time series, e.g., tracking sentiment for many stocks) and offers features like automatic data partitioning (chunking) and columnar compression.65 Available as open-source or a managed cloud service.67
InfluxDB: A custom NoSQL database built from the ground up for time series.65 It uses specialized query languages (InfluxQL, Flux) but also offers SQL compatibility.66 Its schema-less data model can simplify initial setup.65 It may outperform TimescaleDB for very simple aggregation queries or low-cardinality data, and potentially offers better data compression.65 Available as open-source or a managed cloud service.67
Choice Factors: The decision depends on factors like familiarity with SQL vs. NoSQL, the expected complexity of queries (TimescaleDB often better for complex SQL queries/JOINs), data cardinality (TimescaleDB often better for high cardinality), required compression rates (InfluxDB potentially better), and integration with existing tools (TimescaleDB benefits from PostgreSQL compatibility).65
Table: Comparison of Time-Series Databases

Database
Underlying Model
Primary Query Language(s)
Key Strengths
Key Weaknesses
Ecosystem / Integration
TimescaleDB
Relational (PostgreSQL Extension)
SQL
Full SQL support, complex queries, JOINs, high cardinality performance, mature ecosystem 65
Compression might be less than InfluxDB
Leverages extensive PostgreSQL tools & connectors
InfluxDB
Custom NoSQL
InfluxQL, Flux, SQL
Potentially simpler setup (schema-less), good compression, fast simple queries, low cardinality performance 65
Custom query languages, less flexible data model
Growing ecosystem, integrates with monitoring tools

Building this data pipeline is a substantial undertaking. It requires navigating choices across data sources, acquisition methods (with significant cost/reliability trade-offs, especially given the changing API landscape 40), sentiment analysis techniques (where domain specificity matters 61), preprocessing steps, and storage solutions.65 Each stage demands technical expertise and careful consideration, and systems relying on scraping often require ongoing maintenance due to website changes. The feasibility and cost, particularly regarding API access, create a significant gap between what institutional players and independent researchers can readily achieve.
V. Sourcing Market Sentiment Data: Free vs. Paid Options
Acquiring reliable market sentiment data is crucial for analyzing influencer impact. The available sources range from freely accessible indicators and basic data APIs to comprehensive, high-cost institutional platforms. Understanding the capabilities and limitations of each is essential for selecting the appropriate data for the analysis.
A. Utilizing Free Sentiment Indicators and Sources
Several publicly available indicators and tools can offer a general sense of market mood, though often indirectly.
Indirect Market Sentiment Indicators: These typically reflect broad market conditions rather than specific ticker or influencer sentiment:
VIX (CBOE Volatility Index): Often called the "fear index," it measures the market's expectation of 30-day volatility based on S&P 500 option prices. High VIX levels suggest heightened fear and uncertainty.68
Fear & Greed Index: A composite indicator (popularized by CNN) that combines several market variables (e.g., market momentum, stock price strength, put/call ratios) into a single score (0-100) representing dominant investor emotion.68
High-Low Index: Compares the number of stocks reaching 52-week highs to those reaching 52-week lows. Ratios above 70 may indicate bullish sentiment, while below 30 suggest bearishness.68
Put/Call Ratio: Measures the trading volume of put options (bets on price decline) relative to call options (bets on price increase). A rising ratio often indicates increasing bearish sentiment.68
Moving Averages: Technical indicators like the relationship between the 50-day and 200-day moving averages of an index can signal shifts in market trends and underlying sentiment.68
Bullish Percent Index (BPI): Measures the percentage of stocks within a specific index that are currently exhibiting bullish patterns on point-and-figure charts.68
Advance/Decline (A/D) Ratio/Line: A market breadth indicator comparing the number of advancing stocks to declining stocks. It helps gauge overall market participation and potential overbought/oversold conditions.68
Direct Free Sources:
Google Trends: Allows tracking the popularity of search terms (like ticker symbols or influencer names) over time and across regions. While primarily measuring public interest or attention rather than sentiment directly, significant spikes can correlate with market events or shifts in focus.69
Social Media Monitoring Tools (Limited Free Tiers): Some platforms offering social media listening and sentiment analysis (like Brand24 70) might provide limited free trials or very basic free plans, but these are typically insufficient for comprehensive financial analysis.
Limitations of Free Indicators: These indicators are generally broad market gauges, not specific to the sentiment influenced by a particular individual regarding a single stock. They often reflect past behavior or aggregate mood rather than providing granular, real-time, ticker-specific sentiment.68 Google Trends measures search interest, which may not directly translate to positive or negative sentiment.69
B. Free Financial Data APIs: Overview and Evaluation
Free APIs can provide the essential stock price and volume data needed for the analysis pipeline, and some offer limited news or basic sentiment features.
Key Providers and Features:
Alpha Vantage: Offers a popular free tier (e.g., 500 API calls/day) providing historical and real-time data for stocks, forex, and cryptocurrencies, along with technical indicators and fundamental data.38 Limitations: Strict rate limits on the free tier, potential data delays, and possible restrictions on commercial use.39
yfinance: A Python library that scrapes data from Yahoo Finance. It's free and easy to use for fetching historical prices, dividends, splits, and basic company information.38 Limitations: Relies on scraping (unofficial, can break), subject to Yahoo's rate limiting, data might have delays or adjustments not fully transparent.39
IEX Cloud: Provides a free tier (e.g., up to 500,000 "messages" per month) with real-time data primarily for U.S. stocks and ETFs.38 Known for being developer-friendly. Limitations: Free tier usage limits, limited international coverage compared to others.39
Finnhub: Offers real-time stock, forex, and crypto data, plus news, economic indicators, and mentions AI-powered financial sentiment analysis.38 Provides a free tier. Limitations: Free tier is likely significantly restricted in terms of API calls and data access.
Marketstack: Delivers global real-time, intraday, and historical market data covering over 170,000 tickers.38 Includes a free tier. Limitations: Free tier limitations on requests and historical data depth; commercial use likely restricted.38
Twelve Data: Provides real-time and historical data for stocks, forex, crypto, plus technical indicators and news integration.38 Offers a free plan. Limitations: Free plan constraints on API calls and features.
EOD Historical Data (EODHD): Free plan offers 20 API calls/day, limited to recent end-of-day data for specific tickers.14 Notably, their paid tiers ($80/month All-in-One plan mentioned) provide access to a Financial News Feed and Stock News Sentiment data API.14
Evaluation Criteria: When choosing a free API, consider: data coverage (assets, markets), data types provided (price/volume essential, news/sentiment a bonus), data frequency (real-time vs. delayed), API call limits and rate limiting, terms of service (especially regarding commercial use), documentation quality, and ease of integration.38
Table: Comparison of Selected Free/Freemium Financial Data APIs

Provider
Website URL
Key Data Offered
Coverage Focus
Free Tier Limits (Examples)
Commercial Use Allowed?
Key Pro / Con
Alpha Vantage
alphavantage.co
Stocks, Forex, Crypto, Fundamentals, Tech. Indicators
Global
500 calls/day, 5 calls/min 39
Likely Restricted
Pro: Broad data types. Con: Strict limits, potential delays.53
yfinance
(Python Library)
Stocks (Hist. Price, Info, Options)
Global (via Yahoo)
Relies on scraping, rate limits unclear
Check Yahoo Terms
Pro: Easy Python access. Con: Unofficial, fragile, data quirks.39
IEX Cloud
iexcloud.io
Stocks (US focus), ETFs
US Primarily
500k messages/month 39
Tier-dependent
Pro: Real-time US data. Con: Limited free usage, US focus.39
Finnhub
finnhub.io
Stocks, Forex, Crypto, News, Sentiment
Global
Likely limited calls/data access
Tier-dependent
Pro: Offers sentiment. Con: Free tier likely very basic.38
EODHD
eodhistoricaldata.com
Stocks, ETFs, Funds, Indices, News, Sentiment (Paid)
Global
20 calls/day, limited history/tickers 14
No (Free Tier)
Pro: Paid sentiment API. Con: Very limited free tier.14

C. Paid Institutional Data Providers: Features and Costs
For professional analysis, especially requiring high-quality, real-time, granular data, and sophisticated analytics including sentiment, institutional providers are the standard.
Key Providers and Features:
Bloomberg Terminal: The dominant platform (~33% market share 73), offering comprehensive real-time data across all asset classes, integrated news (Bloomberg News), advanced analytics, charting, communication tools (IB chat), and trade execution capabilities.73 Includes sentiment analysis tools derived from news and social media.61 Particularly strong in fixed income data.73 Cost: Approximately $24,000 - $28,000 per terminal per year, typically leased on a two-year contract.73
Refinitiv Eikon (now LSEG Workspace): A major competitor (~20% market share 73), providing extensive real-time global market data, exclusive access to Reuters news, advanced analytics, and trading tools.73 Offers low-latency data suitable for high-frequency applications.76 Cost: Full version around $22,000/year; scaled-down versions can be significantly cheaper ($3,600+); enterprise packages range $20,000-$50,000+ annually.73
FactSet: Known for its strong data integration, analytical capabilities (portfolio analysis, quantitative research), research management tools, and excellent Excel plugin.73 Covers over 90,000 companies globally.76 Cost: Around $12,000 per user per year for a standard subscription; enterprise deals typically $15,000 - $40,000 annually.73
S&P Capital IQ (CapIQ): Renowned for deep fundamental data, detailed company profiles, M&A/transaction screening tools, and extensive coverage of private companies.73 Often considered a strong alternative to Bloomberg for fundamental analysis and corporate finance work. Cost: Pricing is customized and not public, but enterprise subscriptions are estimated to be in the $10,000 - $30,000+ range annually.73
RavenPack: A specialized provider focusing on analyzing unstructured text data (news, filings, social media) to generate analytics, including sophisticated sentiment scores, event detection, and insights for financial markets.61 Likely targets institutional clients with enterprise pricing.
Other Paid Options: Include platforms like Quandl (alternative data focus) 74, and more accessible tools like TIKR, Koyfin, OpenBB, FINVIZ, TradingView, Tiingo, which offer tiered pricing often starting free or low-cost but scaling up for more features/data.75
Sentiment Data Focus: While many platforms offer news, providers like Bloomberg, Refinitiv, and especially RavenPack are known for incorporating or specializing in derived sentiment analytics from text sources.61 Accessing reliable, granular, real-time sentiment specifically linked to tickers or influenced by specific events is far more likely through these paid services than through free indicators or basic APIs.
Table: Comparison of Major Paid Financial Data Providers

Provider
Estimated Annual Cost Range (per user/seat)
Target Audience
Key Data Strengths
Specific Sentiment Analysis Offerings?
Key Pro / Con
Bloomberg Terminal
$24k - $28k 73
Buy/Sell Side, Trading, Asset Management
Real-time multi-asset data, News, Analytics, Fixed Income, Messaging 73
Yes (integrated tools) 61
Pro: Market standard, comprehensive. Con: Very expensive, leased terminal.
Refinitiv Eikon / LSEG Workspace
$4k - $22k+ ($20k-$50k enterprise) 73
Trading, Risk, Research, Wealth Management
Real-time data, Reuters News, Global Coverage, Low Latency 76
Yes (integrated analytics)
Pro: Strong competitor, Reuters news. Con: Can be complex, cost varies significantly.
FactSet
~$12k ($15k-$40k enterprise) 73
Investment Management, Banking, Corp. Finance
Analytics, Portfolio tools, Fundamentals, Excel integration, Global data 76
Yes (as part of analytics)
Pro: Strong analytics, good integration. Con: Less focus on real-time trading/news than Bloomberg/Refinitiv.
S&P Capital IQ
$10k - $30k+ (customized) 73
Investment Banking, PE, Corp. Development
Fundamentals, Company Profiles, Transactions, Private Company Data 73
Less emphasis than others
Pro: Deep fundamental/company data. Con: Pricing opaque, less real-time focus.
RavenPack
Enterprise (Likely High)
Hedge Funds, Quants, Asset Managers
Unstructured data analysis, Event detection, Sentiment/Risk signals 61
Yes (Core offering)
Pro: Specialized in text analytics/sentiment. Con: Niche focus, likely expensive.

D. Guidance on Selecting a Data Provider
The choice between free and paid data sources hinges on the specific requirements of the analysis and available resources:
Assess Needs: Define the exact data required (price, volume, sentiment, news), the necessary coverage (assets, regions), frequency (end-of-day, intraday, real-time), and historical depth.
Consider Budget: Free tiers are suitable for initial exploration, learning, or very small-scale projects. Paid APIs (like EODHD's higher tiers or potentially X's Basic tier) offer a middle ground. Institutional platforms are necessary for professional, real-time, high-volume applications.
Evaluate Limitations: Critically assess the rate limits, data delays, historical data caps, and usage restrictions (personal vs. commercial) of free and low-cost options. These limitations directly impact the feasibility of certain analyses (e.g., real-time monitoring, high-frequency event studies).
Factor in Technical Skills: Consider the effort required for API integration or the complexity of setting up web scrapers versus using a pre-built terminal interface.
The stark difference between the limited, often delayed, and potentially unreliable free data sources and the comprehensive, real-time, but costly institutional platforms creates a significant challenge. Obtaining the high-quality, granular, and timely sentiment data needed for a rigorous analysis of influencer impact likely requires investment in paid solutions. Furthermore, the choice of data source directly constrains the types of analytical methods that can be validly applied; real-time analysis or high-frequency event studies are generally infeasible with free, delayed, or heavily rate-limited data streams.
VI. Conclusion and Strategic Recommendations
Analyzing the correlation and potential causal links between social media influencer activity and market sentiment for specific tickers is a complex but potentially insightful endeavor. This report has outlined several analytical approaches, detailed the construction of a necessary data pipeline, and surveyed the landscape of data sources.
Methodological Summary: Pearson correlation offers a simple starting point for assessing linear association but is constrained by strict assumptions often violated by financial and social data, and crucially, cannot establish causation.10 Alternative methods like Granger causality can test for predictive power but offer a specific, limited definition of causality.20 Regression analysis allows for quantifying impact while controlling for confounding variables but relies on correct model specification.3 Event studies excel at isolating the impact of discrete events but are less suited for continuous influence.19
Data Acquisition and Sourcing Summary: Building a data pipeline involves significant technical choices regarding API access (often costly and restrictive, especially X/Twitter 40) versus web scraping (technically challenging, potentially unreliable 54). Accurate sentiment analysis likely requires domain-specific techniques.61 Data sourcing presents a dichotomy between limited free options (often delayed, rate-limited, or indirect indicators 39) and comprehensive but expensive institutional platforms.73
Strategic Recommendations:
Start Simple, Validate Rigorously: Begin with Pearson correlation analysis using accessible data. However, place significant emphasis on validating assumptions (linearity, normality, outliers, independence) before interpreting results. Be acutely aware that correlation does not imply causation.10
Prioritize Data Quality and Alignment: Invest heavily in data preprocessing. Ensure meticulous cleaning, handling of missing values appropriate for time series, and precise temporal alignment of all data streams (influencer activity, sentiment, market data) to the same frequency. This foundation is critical regardless of the analytical method chosen.13
Employ a Multi-Method Approach: For more robust conclusions, supplement correlation with other techniques if resources permit. Consider Granger causality to test for predictive relationships 19 or regression analysis to estimate impact while controlling for market factors.3 Event studies are valuable for analyzing specific high-impact posts or events.28 Triangulating findings across methods enhances confidence.
Be Realistic About Data Sources and Costs: Acknowledge the severe limitations of free data APIs (rate limits, delays, usage terms).39 If the analysis requires high-quality, granular, real-time, or extensive historical social data (especially from X/Twitter), budget for paid API access or accept the constraints and potential biases of using limited free data or less reliable scraping methods.40
Utilize Domain-Specific Sentiment Analysis: Generic sentiment tools may perform poorly on financial text. Employ or fine-tune models specifically designed for or adapted to the financial domain (e.g., using FinBERT, custom lexicons) to improve the accuracy of sentiment scores.61
Maintain Critical Interpretation and Validation: Treat findings with skepticism. Understand the limitations of each method and data source. Backtest any trading strategies derived from the analysis. Avoid overstating causal claims without strong, converging evidence from multiple perspectives and careful consideration of alternative explanations.
Final Considerations: Successfully navigating this analysis requires a blend of statistical expertise, programming skills (Python for data handling and analysis), financial domain knowledge, and critical thinking to interpret results within context and acknowledge limitations. The influence landscape is dynamic, relationships may change over time (model decay), and ethical considerations surrounding the use of social data must be respected. Given the inherent challenges in data access, quality, and establishing causality in complex market systems, a pragmatic approach focused on robustness—using multiple methods, performing sensitivity analyses, and transparently acknowledging limitations—is ultimately more valuable than pursuing a single, potentially fragile, definitive answer about influencer impact.
Works cited
EasyChair Preprint Correlating Social Media Sentiment with Stock Market Volatility Exploring Relationships Between Sentiment and, accessed April 22, 2025, https://easychair.org/publications/preprint/wQ7X/open
Influence of social media on the stock market: Part 1. A brief analysis - Scientific Publications, accessed April 22, 2025, https://www.scipublications.com/journal/index.php/ujbm/article/view/853
Full article: The impact of social media and internet forums posts on the stock market dynamics: a sentiment analysis using a lexical approach in Borsa İstanbul - Taylor & Francis Online, accessed April 22, 2025, https://www.tandfonline.com/doi/full/10.1080/00036846.2025.2486791?src=
The Rising Power of the Individual Investor: How Social Media Sentiments and User Activity Impact Stock Price Volatility and Trading Volume - Scholarship @ Claremont, accessed April 22, 2025, https://scholarship.claremont.edu/cgi/viewcontent.cgi?article=3941&context=cmc_theses
Stock Market Sentiment Analysis Python Application - LightningChart, accessed April 22, 2025, https://lightningchart.com/blog/python/stock-market-sentiment-analysis/
The Impact of Social Media and the Network Economy on the Stock Market - Advances in Engineering Innovation, accessed April 22, 2025, https://www.ewadirect.com/proceedings/aemps/article/view/18399/pdf
Pearson Correlation Assumptions - Statistics Solutions, accessed April 22, 2025, https://www.statisticssolutions.com/pearson-product-moment-correlation/
A Brief of Pearson's Correlation Coefficient - Julius AI, accessed April 22, 2025, https://julius.ai/articles/a-brief-of-pearsons-correlation-coefficient
Pearson's Correlation Coefficient: A Comprehensive Overview - Statistics Solutions, accessed April 22, 2025, https://www.statisticssolutions.com/free-resources/directory-of-statistical-analyses/pearsons-correlation-coefficient/
Pearson's correlation - Statstutor, accessed April 22, 2025, https://www.statstutor.ac.uk/resources/uploaded/pearsons.pdf
www.scribbr.com, accessed April 22, 2025, https://www.scribbr.com/frequently-asked-questions/assumptions-of-pearson-correlation-coefficient/#:~:text=These%20are%20the%20assumptions%20your,a%20random%20or%20representative%20sample
What are the assumptions of the Pearson correlation coefficient? - Scribbr, accessed April 22, 2025, https://www.scribbr.com/frequently-asked-questions/assumptions-of-pearson-correlation-coefficient/
Sentiment Analysis Usage Within Stock Price Predictions - NHSJS, accessed April 22, 2025, https://nhsjs.com/2025/sentiment-analysis-usage-within-stock-price-predictions/
Financial News Feed and Stock News Sentiment data API | EODHD APIs Documentation, accessed April 22, 2025, https://eodhd.com/financial-apis/stock-market-financial-news-api
ToyotaVision: Financial Insights & Forecasts - Kaggle, accessed April 22, 2025, https://www.kaggle.com/code/pinuto/toyotavision-financial-insights-forecasts
Preprocessing And Cleaning Time Series Data - FasterCapital, accessed April 22, 2025, https://fastercapital.com/topics/preprocessing-and-cleaning-time-series-data.html
Stock Market Sentiment Analysis Python Application - LightningChart, accessed April 22, 2025, https://lightningchart.com/blog/python/stock-market-sentiment-analysis
Python Correlation - A Practical Guide - AlgoTrading101 Blog, accessed April 22, 2025, https://algotrading101.com/learn/python-correlation-guide/
The Effects of Twitter Sentiment on Stock Price Returns - PMC - PubMed Central, accessed April 22, 2025, https://pmc.ncbi.nlm.nih.gov/articles/PMC4577113/
Granger causality - Wikipedia, accessed April 22, 2025, https://en.wikipedia.org/wiki/Granger_causality
5 Insights: Granger Causality Test in 2023 Data Analysis, accessed April 22, 2025, https://www.numberanalytics.com/blog/5-insights-granger-causality-test-in-2023-data-analysis
Advanced Granger Causality Test Applications for Data Science Solutions, accessed April 22, 2025, https://www.numberanalytics.com/blog/advanced-granger-causality-test-applications
Granger Causality in Time Series – Explained using Chicken and Egg problem, accessed April 22, 2025, https://www.analyticsvidhya.com/blog/2021/08/granger-causality-in-time-series-explained-using-chicken-and-egg-problem/
Granger Causality: A Review and Recent Advances - PMC - PubMed Central, accessed April 22, 2025, https://pmc.ncbi.nlm.nih.gov/articles/PMC10571505/
What is Granger Causality Tests - Activeloop, accessed April 22, 2025, https://www.activeloop.ai/resources/glossary/granger-causality-tests/
FinXABSA: Explainable Finance through Aspect-Based Sentiment Analysis - SenticNet, accessed April 22, 2025, https://sentic.net/explainable-finance-through-aspect-based-sentiment-analysis.pdf
Analyzing the Effect of Social Media Sentiment on Stock Prices - ResearchGate, accessed April 22, 2025, https://www.researchgate.net/publication/362454941_Analyzing_the_Effect_of_Social_Media_Sentiment_on_Stock_Prices
Interrelationship between Activities of Social Media and the Stock Market - UQ eSpace - The University of Queensland, accessed April 22, 2025, https://espace.library.uq.edu.au/view/UQ:bd5326f/s4511612_phd_thesis.pdf
Application of Event Study Methodology in the Analysis of Cryptocurrency Returns, accessed April 22, 2025, https://www.tandfonline.com/doi/abs/10.1080/1540496X.2024.2404173
A new event study method to forecast stock returns: The case of Facebook - ResearchGate, accessed April 22, 2025, https://www.researchgate.net/publication/337556174_A_new_event_study_method_to_forecast_stock_returns_The_case_of_Facebook
ESG reputation risk matters: An event study based on social media data - IDEAS/RePEc, accessed April 22, 2025, https://ideas.repec.org/a/eee/finlet/v59y2024ics154461232301084x.html
Full article: The impact of media display events on short-term stock returns: an event study, accessed April 22, 2025, https://www.tandfonline.com/doi/full/10.1080/13504851.2024.2431199?af=R
Causality-Inspired Models for Financial Time Series Forecasting - arXiv, accessed April 22, 2025, https://arxiv.org/pdf/2408.09960
Causality-Inspired Models for Financial Time Series Forecasting - arXiv, accessed April 22, 2025, https://arxiv.org/html/2408.09960v1
Research - Runjing Lu, accessed April 22, 2025, https://www.runjinglu.com/research
The Impact of Social Mood on Stock Markets - UCL Discovery, accessed April 22, 2025, https://discovery.ucl.ac.uk/10078956/1/Souza%20__thesis.pdf
Sentiment Analysis on Twitter with Stock Price and Significant Keyword Correlation - University of Texas at Austin, accessed April 22, 2025, https://repositories.lib.utexas.edu/bitstreams/a00ab8dc-eb53-4240-ae9a-bf1345b7a411/download
Top 5 Free Financial Data APIs for Building a Powerful Stock Portfolio Tracker, accessed April 22, 2025, https://dev.to/williamsmithh/top-5-free-financial-data-apis-for-building-a-powerful-stock-portfolio-tracker-4dhj
Comparing Live Market Data APIs: Which One is Right for Your Project? - DEV Community, accessed April 22, 2025, https://dev.to/williamsmithh/comparing-live-market-data-apis-which-one-is-right-for-your-project-4f71
The X API Price Hike: A Blow to Indie Hackers - We Are Founders, accessed April 22, 2025, https://www.wearefounders.uk/the-x-api-price-hike-a-blow-to-indie-hackers/
X is about to double its API fees - Indie Hackers, accessed April 22, 2025, https://www.indiehackers.com/post/tech/x-is-about-to-double-its-api-fees-y3CoZpvTNU52BSta7h5c
Tweepy, accessed April 22, 2025, https://www.tweepy.org/
How to Make a Twitter Bot in Python With Tweepy, accessed April 22, 2025, https://realpython.com/twitter-bot-python-tweepy/
Extraction of Tweets using Tweepy | GeeksforGeeks, accessed April 22, 2025, https://www.geeksforgeeks.org/extraction-of-tweets-using-tweepy/
praw-dev/praw: PRAW, an acronym for "Python Reddit API Wrapper", is a python package that allows for simple access to Reddit's API. - GitHub, accessed April 22, 2025, https://github.com/praw-dev/praw
Quick Start - PRAW 7.7.1 documentation, accessed April 22, 2025, https://praw.readthedocs.io/en/stable/getting_started/quick_start.html
High School AP Research Project: Need Help Replacing Pushshift API for Reddit Data Collection : r/learnmachinelearning, accessed April 22, 2025, https://www.reddit.com/r/learnmachinelearning/comments/1iios2r/high_school_ap_research_project_need_help/?tl=it
mattpodolak/pmaw: A multithread Pushshift.io API Wrapper for reddit.com comment and submission searches. - GitHub, accessed April 22, 2025, https://github.com/mattpodolak/pmaw
Is there a self-hosted pushshift alternative that would collect just one subreddit of own choice? Or how to go about creating one? : r/redditdev, accessed April 22, 2025, https://www.reddit.com/r/redditdev/comments/13cm4v2/is_there_a_selfhosted_pushshift_alternative_that/
Stocktwits APIs, accessed April 22, 2025, https://rapidapi.com/collection/stocktwits-api
StockTwits API Documentation Free with API Key & SDK | RapidAPI, accessed April 22, 2025, https://rapidapi.com/stocktwits/api/stocktwits
Provide Real-Time Social Sentiment to Customers with Alpaca's Stocktwits Integration, accessed April 22, 2025, https://alpaca.markets/blog/provide-real-time-social-sentiment-to-customers-with-alpacas-stocktwits-integration/
Empowering Financial Insights: Unlocking the Potential of Yahoo Finance API - SmythOS, accessed April 22, 2025, https://smythos.com/ai-integrations/api-integration/yahoo-finance-api/
7 Best Python Web Scraping Libraries in 2025 - ZenRows, accessed April 22, 2025, https://www.zenrows.com/blog/python-web-scraping-library
Top 5 Python Web Scraping Libraries in 2025 - Roborabbit, accessed April 22, 2025, https://www.roborabbit.com/blog/top-5-python-web-scraping-libraries-in-2025/
Top 7 Python Web Scraping Libraries - Bright Data, accessed April 22, 2025, https://brightdata.com/blog/web-data/python-web-scraping-libraries
Comparison of Web Scraping Tools and Libraries - UseScraper, accessed April 22, 2025, https://usescraper.com/blog/comparison-of-web-scraping-tools-and-libraries
Sentiment Analysis in NLP: Key Techniques and Insights - Sapien, accessed April 22, 2025, https://www.sapien.io/blog/sentiment-analysis-in-nlp
A Comprehensive Guide to Sentiment Analysis Using NLP - Codalien Technologies, accessed April 22, 2025, https://codalien.com/blog/how-to-implement-sentiment-analysis-in-python/
Five Approaches to Sentiment Analysis | IMA - Strategic Finance, accessed April 22, 2025, https://www.sfmagazine.com/articles/2023/june/five-approaches-to-sentiment-analysis
NLP for Financial Sentiment Analysis - PyQuant News, accessed April 22, 2025, https://www.pyquantnews.com/free-python-resources/nlp-for-financial-sentiment-analysis
From Deep Learning to LLMs: A survey of AI in Quantitative Investment - arXiv, accessed April 22, 2025, https://arxiv.org/html/2503.21422v1
Fine-Tuning GPT-4o Mini for Financial Sentiment Analysis - Analytics Vidhya, accessed April 22, 2025, https://www.analyticsvidhya.com/blog/2024/11/financial-sentiment-analysis/
6 Must-Know Python Sentiment Analysis Libraries - Netguru, accessed April 22, 2025, https://www.netguru.com/blog/python-sentiment-analysis-libraries
TimescaleDB vs. InfluxDB: Purpose Built Differently for Time-Series Data, accessed April 22, 2025, https://www.timescale.com/blog/timescaledb-vs-influxdb-for-time-series-data-timescale-influx-sql-nosql-36489299877
Which Time-Series Database is Better: TimescaleDB vs InfluxDB | Severalnines, accessed April 22, 2025, https://severalnines.com/blog/which-time-series-database-better-timescaledb-vs-influxdb/
The Best Time-Series Databases Compared - Timescale, accessed April 22, 2025, https://www.timescale.com/learn/the-best-time-series-databases-compared
How to Analyze Market Sentiment Indicators to Grow Client Portfolios - SmartAsset, accessed April 22, 2025, https://smartasset.com/advisor-resources/market-sentiment-indicator
6 Powerful Real-Time Stock Market Sentiment Analysis Tools, accessed April 22, 2025, https://www.strikingly.com/blog/posts/6-powerful-real-time-stock-market-sentiment-analysis-tools
How to Do Market Sentiment Analysis? 6-Steps Guide & Nvidia Example - Brand24, accessed April 22, 2025, https://brand24.com/blog/market-sentiment-analysis/
Is there any free stock market API that allows publishing on a website? - Reddit, accessed April 22, 2025, https://www.reddit.com/r/webdev/comments/151zk8y/is_there_any_free_stock_market_api_that_allows/
Top 7 Financial APIs to Try Out in 2024 - InsightBig, accessed April 22, 2025, https://www.insightbig.com/post/top-7-financial-apis-to-try-out-in-2024
Bloomberg vs. Capital IQ (CapIQ) vs. Factset vs. Refinitiv - Wall Street Prep, accessed April 22, 2025, https://www.wallstreetprep.com/knowledge/bloomberg-vs-capital-iq-vs-factset-vs-thomson-reuters-eikon/
Best Financial Data Analysis Platforms solutions 2025 - PeerSpot, accessed April 22, 2025, https://www.peerspot.com/categories/financial-data-analysis-platforms
Free and low cost alternatives to Bloomberg - Hudson Labs, accessed April 22, 2025, https://www.hudson-labs.com/post/free-and-low-cost-alternatives-to-bloomberg
Capital IQ vs. FactSet vs. Refinitiv | CFI - Corporate Finance Institute, accessed April 22, 2025, https://corporatefinanceinstitute.com/resources/capital_markets/capital-iq-vs-factset-vs-refinitiv/