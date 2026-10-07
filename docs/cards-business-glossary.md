# **Cards Agent Vocabulary**

---

## **1\. Customers**

| Term | Definition | Synonyms |
| :---- | :---- | :---- | 
| MAU | Users with transactions in the past 30 days | MAU, monthly active users, engaged users, current users |
| Dormant | Users with no transaction in the past 30 days and hence are considered **not active**. Their account is still open, the users are simply not “financially active”. | inactive users, churned customers, lapsed users, sleeping accounts, non-active, Non MAU, lapser |

---

## **2\. Chargebacks**

| Term | Definition | Synonyms |
| :---- | :---- | :---- |
| Chargeback | chargebacks table | dispute, transaction dispute, contested transaction, CB, disputed charge , chb |

---

## **3\. Digital Wallets (Tokenization)**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| Days to Tokenize | days\_to\_tokenize | time to tokenize, tokenization timing, days until tokenization, wallet activation time |
| Tokenization | tokenizations table | digital wallet, wallet provisioning, card tokenization, mobile wallet, contactless setup |

---

## **4\. Transaction Attributes**

| Term | Definition | Synonyms |
| :---- | :---- | :---- |
| authorization |  | AA | auth |
| presentment |  | PT |  |

---

## **5\. Metrics & Measures**

| Term | Definition | Synonyms | 
| :---- | :---- | :---- |
| Chargeback Rate | COUNT(chargebacks) / COUNT(transactions) | dispute rate, CB rate, chargeback percentage |
| Transaction Volume | COUNT(\*) on transactions | txn volume |
| Total Spend | SUM(amount\_cents) | total amount, gross spend, spend volume, revenue, GMV |
| Average Transaction | AVG(amount\_cents) | avg txn, average spend, mean transaction, ATV |
| Average Cards | COUNT(cards) / COUNT(customers) | cards per customer, avg cards per user, card density |

---

## **6\. Time-Based Query Terms**

| Term | Interpretation | Synonyms | 
| :---- | :---- | :---- | 
| Last Week | Previous 7 days | past week, previous week, last 7 days, week ago |
| This Week | Current week | current week, this 7 days |
| Last Month | Previous calendar month | past month, previous month, last 30 days |
| This Month | Current calendar month | current month, MTD, month to date |
| Yesterday | Previous day | last day, day before, previous day |
| Today | Current day | current day, now |
| Q1/Q2/Q3/Q4 | Calendar quarters | first quarter, second quarter, third quarter, fourth quarter |
| YTD | Year to date | this year, year to date, current year |

---

## **7\. Trend & Analysis Terms**

| Term | Context | Synonyms |
| :---- | :---- | :---- |
| Spike | Sudden increase | surge, jump, sharp increase, anomaly, peak |
| Increase | Growth | rise, growth, uptick, higher, went up, grew |
| Decrease | Decline | drop, decline, fall, reduction, went down, lower |
| Trend | Pattern over time | pattern, trajectory, direction, movement |
| Compare | Side-by-side analysis | versus, vs, compared to, difference between, contrast |
| Breakdown | Segmented view | split by, grouped by, by category, distribution, segmentation |

---

## **8\. Action Verbs (Natural Language Query Starters)**

| Term | Intent | Synonyms | 
| :---- | :---- | :---- | 
| Show me | Display data | display, list, give me, what is, what are, find |
| How many | Count query | count, number of, total count, quantity of |
| How much | Sum/amount query | total, sum, amount of, what's the total |
| Why did | Root cause analysis | what caused, reason for, explain why, root cause |
| What type | Category query | which kind, what category, which type |
| Where | Location/filter query | in which, which country, which region |
| When | Time query | what time, which period, what date |
| Who | Entity identification | which customers, which merchants, which users |
| Bottom | Reverse ranking | lowest, worst, least, smallest, fewest |
| Top | Ranking query | highest, best, most, leading, largest |

---

## **9\. Entity Names**

| Term | Table | Synonyms |
| :---- | :---- | :---- |
| Customer | customers | user, client, account holder, cardholder, member |
| Card | cards | payment card, bank card, plastic, card product |
| Merchant | merchants | vendor, store, retailer, seller, business, shop |
| Transaction | transactions | purchase, payment, charge, sale, txn |
| Tokenization | tokenizations | wallet provisioning, digital wallet setup, token |
| Chargeback | chargebacks | dispute, CB, reversal, contested charge |

---