💎 Membership Pricing Model (USD-Pegged, FAP-Paid)
Overview

WAPClub membership is paid exclusively in FAPCOIN (SPL token on Solana).

However, pricing is pegged to fixed USD values to ensure consistency regardless of token volatility.

Members always pay in FAP —
but the required FAP amount is dynamically calculated based on the current USD price of FAP.

📦 Membership Packages
Package	USD Price	Duration
Starter	$100	6 Months
Pro	$150	1 Year
Elite	$200	2 Years
Lifetime	$500	Lifetime

All payments must be made in FAPCOIN.

💰 Pricing Logic

Membership pricing follows a USD-pegged model:

Required FAP Amount = USD Package Price ÷ Current FAP/USD Price

Example:

If FAP price = $0.02

$100 package → 100 ÷ 0.02 = 5,000 FAP

$150 package → 150 ÷ 0.02 = 7,500 FAP

$200 package → 200 ÷ 0.02 = 10,000 FAP

$500 package → 500 ÷ 0.02 = 25,000 FAP

If FAP price rises, required FAP decreases.
If FAP price falls, required FAP increases.

This ensures:

Stable USD value

Sustainable ecosystem

Protection from volatility

Long-term pricing fairness

🔄 Price Source

The system retrieves the live FAP/USD price from:

On-chain DEX data (Raydium pool)

Or price API provider

Or internal oracle logic

The price is cached briefly (e.g., 30–60 seconds) to avoid manipulation.

🧠 Payment Flow (Dynamic Calculation)

User selects membership tier.

Bot fetches current FAP/USD price.

Bot calculates required FAP amount.

Bot displays:

Exact FAP required

Payment wallet address

Unique reference ID

User sends FAP.

Bot verifies exact or greater amount.

Membership activated.

🛡 Anti-Manipulation Design

To prevent price abuse:

Price snapshot is locked per transaction session.

Minimum slippage tolerance may be applied.

Price source must be verified.

Required FAP amount is rounded safely (never undercharge).

📈 Economic Impact

This model creates:

Continuous FAP demand

Real token utility

Buy pressure during growth

Sustainable revenue model

Long-term value alignment

Every member must acquire FAP before access.

No FAP = No Access.
