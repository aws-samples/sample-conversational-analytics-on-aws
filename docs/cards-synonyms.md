# **Cards Semantic Layer**

---

## **1\. Customer Segments**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- | 
| Active | user\_status \= 'active' | MAU, monthly active users, engaged users, current users |
| Dormant | user\_status \= 'dormant' | inactive users, churned customers, lapsed users, sleeping accounts, non-active ✅ | Non MAU |

---

## **2\. Customer Types**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- | :---- |
| Personal | customer\_type \= 'personal' | individual, consumer, retail customer, private customer, B2C, Perso |
| Business | customer\_type \= 'business' | corporate, company, B2B, commercial, SMB, business account, Biz |

---

## **3\. Card Types**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| Virtual | card\_type \= 'virtual' |  |
| Physical | card\_type \= 'physical' |  |

---

## **4\. Membership Tiers**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| Standard | membership\_tier \= 'standard' | Std, free account |
| Plus | membership\_tier \= 'plus' |  |
| Gold | membership\_tier \= 'gold' |  |
| Metal | membership\_tier \= 'metal' |  |
| Select | membership\_tier \= 'select' |  |

---

## **5\. Card Networks**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| Mastercard | card\_network \= 'mastercard' | MC, Mastercard, Master Card |

---

## **6\. Delivery Types**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| Express | delivery\_type \= 'express' | fast delivery, priority shipping, expedited, rush delivery, next-day, quick delivery |
| Standard | delivery\_type \= 'standard' | normal delivery, regular shipping, standard shipping, economy delivery |
| Delivery Time | DATE\_DIFF(issue\_date, delivery\_date) | shipping time, time to deliver, days to deliver, delivery days, fulfillment time, Delivery time |

---

## **7\. Order Types**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| Initial | order\_type \= 'initial' | first card, Bundle card, bundled card, membership card |
| Reorder | order\_type \= 'reorder' | replacement, re-issue, new copy, duplicate |
| Replacement Expired | order\_type \= 'replacement\_expired' | expired replacement, renewal, expiry replacement, card renewal |
| Additional | order\_type \= 'additional' | Non bundled |

---

## **8\. Campaign Codes**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| XMAS\_2025 | campaign\_code \= 'XMAS\_2025' | Xmas card, Christmas card, Christmas special, Christmas 2025, Xmas special |
| Special Edition | campaign\_code IS NOT NULL | promotional card, limited edition, campaign card, special card, promo card |
| Regular Card | campaign\_code IS NULL | standard card, non-promotional, regular edition, base card |

---

## **9\. Chargeback Types**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| Unauthorized | chargeback\_type \= 'unauthorized' | fraud, fraudulent transaction, not authorized, stolen card, fraud dispute, unauthorized transaction, Unauth |
| Authorized | chargeback\_type \= 'authorized' | legitimate dispute, non-fraud dispute, merchant dispute, service dispute, product dispute, auth |

---

## **10\. Chargeback Reason Codes**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| Fraud Card Not Present | reason\_code \= 'fraud\_card\_not\_present' | CNP fraud, online fraud, remote fraud, card-not-present, e-commerce fraud |
| Fraud Counterfeit | reason\_code \= 'fraud\_counterfeit' | fake card, cloned card, counterfeit card, skimmed card, card cloning |
| Fraud Lost Stolen | reason\_code \= 'fraud\_lost\_stolen' | lost card, stolen card, missing card, card theft |
| Merchandise Not Received | reason\_code \= 'merchandise\_not\_received' | item not received, goods not delivered, non-delivery, package not arrived, missing order, Service not received |
| Merchandise Defective | reason\_code \= 'merchandise\_defective' | defective item, damaged goods, broken product, faulty merchandise, quality issue, Goods not as described |
| Duplicate Charge | reason\_code \= 'duplicate\_charge' | double charge, charged twice, duplicate transaction, double billing, Duplicate processing |
| Incorrect Amount | reason\_code \= 'incorrect\_amount' | wrong amount, overcharge, billing error, amount mismatch, Difference in amount, unreasonable amount |
| Subscription Cancelled | reason\_code \= 'subscription\_cancelled' | cancelled subscription, recurring charge after cancel, unwanted renewal, subscription dispute |

---

## **11\. Chargeback Status**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| Pending | status \= 'pending' | open, in progress, under review, unresolved, active dispute |
| Won | status \= 'won' | User won, refunded, accepted, merchant lost |
| Lost | status \= 'lost' | User lost, not refunded, rejected, merchant won |
| Expired | status \= 'expired' | timed out, closed, expired dispute, No response |

---

## **12\. Digital Wallets (Tokenization)**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| Apple Pay | wallet\_type \= 'apple\_pay' | Apple Wallet, iOS Pay, iPhone wallet, Apple payment |
| Google Pay | wallet\_type \= 'google\_pay' | GPay, Google Wallet, Android Pay, Google payment |
| Samsung Pay | wallet\_type \= 'samsung\_pay' | Samsung Wallet, Samsung payment |
| Garmin pay | wallet\_type \= 'garmin\_pay' | Garmin Wallet, Runner wallet |
| Days to Tokenize | days\_to\_tokenize | time to tokenize, tokenization timing, days until tokenization, wallet activation time |

---

## **13\. Merchant Channels**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| POS | channel \= 'pos' | in-store, point of sale, retail, physical store, brick and mortar, in-person, chip and pin |
| ECOM | channel \= 'ecom' | online, e-commerce, web purchase, internet purchase, digital, online store |
| ATM | channel \= 'atm' | Withdraw, cash machine, Geldautomat |

---

## **14\. Merchant Category Codes (MCCs)**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| Groceries | merchant\_category\_code \= '5411' | grocery stores, supermarket, food shopping, grocery shopping |
| Gas Stations | merchant\_category\_code \= '5541' | petrol stations, fuel, gas, filling station, service station |
| Restaurants | merchant\_category\_code \= '5812' | dining, eating out, restaurant spending, food & beverage |
| Fast Food | merchant\_category\_code \= '5814' | quick service, QSR, fast casual, takeaway, takeout |
| Airlines | merchant\_category\_code \= '3000' | flights, air travel, airline tickets, flight purchases |
| Hotels | merchant\_category\_code \= '7011' | accommodation, lodging, hotel bookings, hospitality |
| Travel | merchant\_category\_code \= '4722' | travel agencies, vacation, trips, travel bookings |
| Pharmacies | merchant\_category\_code \= '5912' | drugstore, chemist, pharmacy purchases |
| Department Stores | merchant\_category\_code \= '5311' | department store, big-box retail |
| Clothing Stores | merchant\_category\_code \= '5691' | apparel, fashion, clothes shopping, clothing retail |
| Jewelry Stores | merchant\_category\_code \= '5944' | jewelry, jewellery, accessories, watch stores |
| Toy Stores | merchant\_category\_code \= '5945' | toys, games, toy shops, children's retail |
| Electronics | merchant\_category\_code \= '5732' | electronics stores, tech, gadgets, consumer electronics |
| Direct Marketing | merchant\_category\_code \= '5964' | e-commerce, online retail, direct sales |
| MCC | merchant\_category\_code | merchant category, category code, industry code |

---

## **15\. Countries** 

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| ES | country \= 'ES' | Spain, Spanish, Espana, ESP |
| DE | country \= 'DE' | Germany, German, Deutschland, DEU |
| UK | country \= 'UK' | United Kingdom, Britain, British, England, GB |
| FR | country \= 'FR' | France, French, FRA |
| IT | country \= 'IT' | Italy, Italian, Italia, ITA |
| NL | country \= 'NL' | Netherlands, Dutch, Holland, NLD |
| PL | country \= 'PL' | Poland, Polish, Polska, POL |
| PT | country \= 'PT' | Portugal, Portuguese, POR |

---

## **16\. Transaction Attributes**

| Term | Column/Value | Synonyms |
| :---- | :---- | :---- |
| Approved | is\_approved \= true | successful, completed, authorized, accepted, processed, Presentment, authorization |
| Declined | is\_approved \= false | rejected, failed, denied, unsuccessful, blocked |
| Amount | amount\_cents | transaction amount, purchase amount, spend, value, total |
| Transaction | transactions table | purchase, payment, charge, txn, transaction |

---

## **17\. Metrics & Measures**

| Term | Column/Value | Synonyms | 
| :---- | :---- | :---- |
| Chargeback Rate | COUNT(chargebacks) / COUNT(transactions) | dispute rate, CB rate, chargeback percentage |
| Transaction Volume | COUNT(\*) on transactions | txn volume |
| Total Spend | SUM(amount\_cents) | total amount, gross spend, spend volume, revenue, GMV |
| Average Transaction | AVG(amount\_cents) | avg txn, average spend, mean transaction, ATV |
| Average Cards | COUNT(cards) / COUNT(customers) | cards per customer, avg cards per user, card density |

---

## **18\. Time-Based Query Terms**

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

## **19\. Trend & Analysis Terms**

| Term | Context | Synonyms |
| :---- | :---- | :---- |
| Spike | Sudden increase | surge, jump, sharp increase, anomaly, peak |
| Increase | Growth | rise, growth, uptick, higher, went up, grew |
| Decrease | Decline | drop, decline, fall, reduction, went down, lower |
| Trend | Pattern over time | pattern, trajectory, direction, movement |
| Compare | Side-by-side analysis | versus, vs, compared to, difference between, contrast |
| Breakdown | Segmented view | split by, grouped by, by category, distribution, segmentation |

---

## **20\. Action Verbs (Natural Language Query Starters)**

| Term | Intent | Suggested Synonyms | PM Additions |
| :---- | :---- | :---- | :---- |
| Show me | Display data | display, list, give me, what is, what are, find |  |
| How many | Count query | count, number of, total count, quantity of |  |
| How much | Sum/amount query | total, sum, amount of, what's the total |  |
| Why did | Root cause analysis | what caused, reason for, explain why, root cause |  |
| What type | Category query | which kind, what category, which type |  |
| Where | Location/filter query | in which, which country, which region |  |
| When | Time query | what time, which period, what date |  |
| Who | Entity identification | which customers, which merchants, which users |  |
| Top | Ranking query | highest, best, most, leading, largest |  |
| Bottom | Reverse ranking | lowest, worst, least, smallest, fewest |  |

---

## **21\. Entity Names**

| Term | Table | Suggested Synonyms | PM Additions |
| :---- | :---- | :---- | :---- |
| Customer | customers | user, client, account holder, cardholder, member |  |
| Card | cards | payment card, bank card, plastic, card product |  |
| Merchant | merchants | vendor, store, retailer, seller, business, shop |  |
| Transaction | transactions | purchase, payment, charge, sale, txn |  |
| Tokenization | tokenizations | wallet provisioning, digital wallet setup, token |  |
| Chargeback | chargebacks | dispute, CB, reversal, contested charge |  |

---