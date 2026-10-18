# EMI Calculator Android — Product Journey Map (JMIP)

> **Source of Truth**: `emi_calc/` (cloned from `kalagato-inc/EMI-Calc-Andriod`)
> **Analytics Engine**: `ViewUtils.LoggerEvent_for_Location` and `ViewUtils.set_FirebaseAnalytics_Events`
> **Event Namespace Legend**:
> - `LoggerEvent_for_Location` → fires `logEvent` with `location` param (screen-scoped)
> - `set_FirebaseAnalytics_Events` → fires `logEvent` with no extra param (action-scoped)
> - `LoggerEvent_for_Other` → fires `logEvent` with `other` string param (value-scoped)

---

## Branch Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Happy path / Success branch |
| ⚠️ | Error / Validation failure branch |
| ⏭️ | Skip / Bypass branch |
| 🔄 | Re-entry / Loop back |
| 💀 | Dead end / Flow terminates |
| 💰 | Monetisation gate (paywall / ad) |
| 🔔 | Background / system trigger |

---

## JOURNEY 1: First-Time Open / Onboarding

**Entry**: App installed fresh → `OnboardingActivity`
**File**: [`OnboardingActivity.kt`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/newFeature/onboarding/OnboardingActivity.kt)

| Step | Screen / State | Event | Branch | Next |
|------|---------------|-------|--------|------|
| 1 | Onboarding slide 1 shown | *(none — no event on first slide load)* | — | Slide 2 |
| 2 | User swipes → Slide 2 | *(loadAdEveryTime — no named GA event)* | ✅ forward | Slide 3 |
| 2b | User presses **Skip** button | *(no explicit skip event)* | ⏭️ skip | `gotoMainActivity()` |
| 3 | Last slide shown — Next button changes to "Finish" | *(no event)* | ✅ | `gotoMainActivity()` |
| 4 | `gotoMainActivity()` checks onboarding status | — | — | — |
| 4a | `oldOnboarding=true && newOnboarding=true` | — | ✅ new flow | → `SelectCurrencyActivity` |
| 4b | Any other state | — | ✅ default | → `showInterstitialAndContinue()` |
| 5 | `showInterstitialAndContinue()` — `showSplashInterstitialNewUser=true` AND cap allows | 💰 Interstitial load attempt | — | — |
| 5a | Interstitial loaded successfully | — | ✅ | Ad shown → `proceedToPaywallOrMain()` |
| 5b | Interstitial load **fails** (`onAdFailedToLoad`) | — | ⚠️ ad fail | `proceedToPaywallOrMain()` |
| 5c | `showSplashInterstitialNewUser=false` OR cap exceeded | — | ⏭️ skip ad | `proceedToPaywallOrMain()` |
| 6 | `proceedToPaywallOrMain()` — user is **Pro** | — | ⏭️ pro skip | → `Main_Activity` |
| 6a | `shouldShowPaywall()=true` | — | 💰 paywall | → `PaywallActivity` |
| 6b | `shouldShowPaywall()=false` | — | ✅ | → `Main_Activity` |

**Back-press during onboarding**: If on page 0 → `finish()` (💀 app exits). Else → previous slide.

---

## JOURNEY 2: Paywall (Subscription Gate)

**Entry**: From Onboarding, or from Premium icon click in Main Activity
**File**: [`PaywallActivity.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/PaywallActivity.java)

| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | Paywall shown (RevenueCat UI) | *(no GA event on open)* | — | User action |
| 2a | User **purchases** subscription | *(no named GA event)* | ✅ purchased | `RevenueCatHelper.getCustomerInfo()` → `Main_Activity` after 1s delay |
| 2b | User **restores** purchase | *(no named GA event)* | ✅ restored | Same as 2a |
| 2c | User **cancels** paywall | *(no named GA event)* | ⏭️ cancelled | → `Main_Activity` |
| 2d | RevenueCat **error** | *(no named GA event)* | ⚠️ error | Toast "Subscription Error!" → `Main_Activity` |

**Note**: No GA events are fired from `PaywallActivity`. Subscription status change is tracked server-side via RevenueCat.

---

## JOURNEY 3: Dashboard (Home Screen)

**Entry**: `Main_Activity` → loads `Home_Fragment` as default
**Files**: [`Main_Activity.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/navigationView/Main_Activity.java), [`Home_Fragment.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/navigationView/fragment/Home_Fragment.java)

### 3.1 Dashboard Load
| Step | Screen | Event | Branch | Next |
|------|--------|-------|--------|------|
| 1 | `Main_Activity.showAftrerAdsClose()` | `dashboard_viewed` | ✅ | Home rendered |
| 2 | Home layout variant check via Remote Config | *(no event)* | — | V1 or V2 layout |
| 3 | Banner ad loaded (free user) | *(no event)* | 💰 ad | Banner visible |
| 3b | Pro user detected | *(no event)* | ⏭️ pro | Banner hidden |
| 4 | News fragment embedded in home | `Home_news_viewed` (on news appear) | — | News cards |

### 3.2 Dashboard Navigation Clicks (Bottom Nav)
| Click | Event | Destination |
|-------|-------|-------------|
| Bottom nav → **Home** | `footer_menu_home_clicked` | `Home_Fragment` |
| Bottom nav → **EMI Calculator** | `footer_menu_emi_cal_clicked` | `EMI_Fragment` |
| Bottom nav → **Compare Loans** | `footer_menu_compare_loan_clicked` | `Compare_Loan_Fragment` |

### 3.3 Hamburger Drawer Navigation
| Click | Event | Destination |
|-------|-------|-------------|
| Drawer → EMI Calculator | `hm_emi_calculator_clicked` | `EMI_Fragment` |
| Drawer → Compare Loans | `hm_compare_loans_clicked` | `Compare_Loan_Fragment` |
| Drawer → Currency Converter | `hm_currency_conv_clicked` | `Currency_Fragment` |
| Drawer → GST Calculator | `hm_gst_cal_clicked` | `Gst_Calculator_Fragment` |
| Drawer → SIP Calculator | `hm_sip_cal_clicked` | `SPICalculatorFragment` |
| Drawer → FD Calculator | `hm_fd_cal_clicked` | `FDFragment` |
| Drawer → RD Calculator | `hm_rd_cal_clicked` | `FDFragmentRD` |
| Drawer → PPF Calculator | `hm_ppf_cal_clicked` | `FDFragmentPPF` |
| Drawer → Settings | `setting_setting_clicked` | `Settings_Fragment` |
| Drawer → Join WhatsApp | `hm_Join_whatsapp_clicked` | External WhatsApp URL |
| Drawer → Share | *(no event)* | Share intent |
| Drawer → Privacy Policy | *(no event)* | External browser |
| Premium icon click | *(no event)* | `PaywallActivity` |

### 3.4 Home Fragment Tool Clicks
| Click | Event | Branch | Destination |
|-------|-------|--------|-------------|
| EMI Calculator card | *(no event — navigates directly)* | ✅ | `EMI_Fragment` |
| Compare Loans card | *(no event — navigates directly)* | ✅ | `Compare_Loan_Fragment` |
| FD (V1 layout) | `hm_fd_cal_clicked` (from drawer) | ✅ | `FDFragment` |
| FD (V2 layout) | *(no event)* | ✅ | `FragmentActivity` with `FDFragment` |
| RD / PPF / SIP / GST / Currency (V2) | — | ✅ | `FragmentActivity` with respective tag |
| Currency Converter (V2) | `dashboard_currency_conv_clicked` | ✅ | `FragmentActivity` + `Currency_Fragment` |
| See All finance tools | `home_finance_see_all_clicked` | ✅ | `AllFinanceToolActivity` |
| WebView Feature tile click (Free + ads) | `WebView_Calculator_CLICKED_<featureName>` | 💰 interstitial shown | WebView after ad |
| WebView Feature tile — **ad loaded** | `WebView_Calculator_AD_COMPLETE_<featureName>` | ✅ | WebView opens |
| WebView Feature tile — **no ad / pro** | `WebView_Calculator_NO_ADS_<featureName>` | ⏭️ | WebView opens directly |
| View More News | *(no event)* | ✅ | `EmiNews` activity |
| Share (whatsapp icon) | `Home_share_clicked` | ✅ | System share intent |
| News card click | `Home_news_clicked` | ✅ | News detail screen |
| News share | `News_share_clicked` | ✅ | Share intent |
| Part Payment (V2) | *(no event)* | ✅ | WebView `extra-loan-spark.lovable.app` |
| TVM Calculator (V2) | *(no event)* | ✅ | WebView `emi-zen-planner.lovable.app/tvm` |

---

## JOURNEY 4: EMI Calculator Core Flow

**Entry**: `EMI_Fragment` (from any navigation path)
**File**: [`EMI_Fragment.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/navigationView/fragment/EMI_Fragment.java)

### 4.1 Tab Selection (Solve-For Mode)
| Tab Clicked | Event | selectedItem value | Field locked (output) |
|-------------|-------|-------------------|----------------------|
| **EMI** tab (default) | `emi_calculator_emi_tab_clicked` | 4 | EMI field |
| **Loan Amount** tab | `emi_calculator_loan_amount_clicked` | 1 | Loan Amount field |
| **Interest Rate** tab | `emi_calculator_interest_clicked` | 2 | Interest field |
| **Period** tab | `emi_calculator_period_clicked` | 3 | Year + Month fields |

### 4.2 Calculate Button — Per Mode

#### Mode: Solve EMI (selectedItem=4) → `findEMI()`
| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | User taps Calculate | `emi_calculator_calculate_clicked` | — | Validation |
| 2 | Loan Amount ≤ 0 | — | ⚠️ error | Red border on field, `return false` |
| 3 | Interest Rate ≤ 0 | — | ⚠️ error | Red border, `return false` |
| 4 | Year AND Month both empty | — | ⚠️ error | Red border both, `return false` |
| 5 | Year + Month both = 0 | — | ⚠️ error | Red border both, `return false` |
| 6 | Interest > 50% | — | ⚠️ validation guard | Field auto-reset to 0 (TextWatcher) |
| 7 | All valid → EMI computed | — | ✅ | EMI displayed in locked field |
| 8 | `parsedEmi * months >= loanAmount` check | — | ✅ | → `Calculate_Details_Activity` |
| 8b | Check fails | — | ⚠️ invalid data | EMI field cleared, error borders shown |
| 9 | DB insert (SQLite history) | — | ✅ | Record saved to `TABLE_NAME_EMI_HOME` |
| 10 | Navigation to `Calculate_Details_Activity` | — | ✅ | Details screen opened |

#### Mode: Solve Loan Amount (selectedItem=1) → `findLoanAmount()`
| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | Calculate tapped | `emi_calculator_loan_amt_cal_clicked` | — | Validation |
| 2 | EMI ≤ 0 | — | ⚠️ | Red border EMI |
| 3 | Interest ≤ 0 | — | ⚠️ | Red border Interest |
| 4 | Year + Month both empty/zero | — | ⚠️ | Red border both period fields |
| 5 | Interest > 50 | — | ⚠️ | Red border Interest |
| 6 | All valid → `loan_Amount` computed | — | ✅ | Loan Amount field populated, → details |

#### Mode: Solve Interest Rate (selectedItem=2) → `findInterestRate()`
| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | Calculate tapped | `emi_calculator_interest_cal_clicked` | — | Validation |
| 2 | Loan Amount ≤ 0 | — | ⚠️ | Red border |
| 3 | EMI ≤ 0 | — | ⚠️ | Red border |
| 4 | Year + Month both empty/zero | — | ⚠️ | Red border |
| 5 | `n <= 0 OR EMI > LoanAmount` | — | ⚠️ | Toast "Enter valid data" |
| 6 | Binary search converges | — | ✅ | Interest field populated, → details |

#### Mode: Solve Period (selectedItem=3) → `findPeriod()`
| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | Calculate tapped | `emi_calculator_period_cal_clicked` | — | Validation |
| 2 | Loan Amount ≤ 0 | — | ⚠️ | Red border |
| 3 | Interest ≤ 0 | — | ⚠️ | Red border |
| 4 | EMI ≤ 0 | — | ⚠️ | Red border |
| 5 | `EMI > LoanAmount` OR params invalid | — | ⚠️ | Red border all 3 fields |
| 6 | Amortization loop (max 600 months) | — | ✅ | Year + Month fields populated, → details |

### 4.3 Reset Button
| State | Event | Branch | Next |
|-------|-------|--------|------|
| Reset in EMI mode (selectedItem=4) | `emi_calculator_reset_clicked` | 🔄 | All fields cleared, results hidden |
| Reset in Loan Amount mode | `emi_calculator_loan_amt_reset_clicked` | 🔄 | All fields cleared |
| Reset in Interest mode | `emi_calculator_interest_reset_clicked` | 🔄 | All fields cleared |
| Reset in Period mode | `emi_calculator_period_reset_clicked` | 🔄 | All fields cleared |

### 4.4 History Icon (EMI Fragment toolbar)
| Click | Event | Destination |
|-------|-------|-------------|
| History icon (img_history) | `emi_calculator_history_clicked` | `HistoryList_Activity` |
| History option menu item | `emi_calculator_history_clicked` | `HistoryList_Activity` |

### 4.5 Deeplink Entry into EMI Fragment
If launched via deeplink with pre-filled data:
- `deeplink_amount`, `deeplink_rate`, `deeplink_year`, `deeplink_month`, `deeplink_emi` → fields pre-populated
- No specific GA event for deeplink fill, but `emi_calculator_calculate_clicked` fires when user taps Calculate

---

## JOURNEY 5: Calculation Details Screen

**Entry**: `Calculate_Details_Activity` (always from successful Calculate tap in EMI_Fragment)
**File**: [`Calculate_Details_Activity.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/Details/Calculate_Details_Activity.java)

| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | Screen loads | *(no open event)* | — | Pie chart + summary shown |
| 2 | Ad type from Remote Config | *(no event)* | — | Banner or Native ad loaded |
| 2a | Pro user | *(no event)* | ⏭️ | No ad shown |
| 3 | **Amortisation Details** button tap | *(event fires via interstitial flow)* | 💰 interstitial gate | — |
| 3a | `emi_details_interstitial=true` AND cap allows AND not pro | — | 💰 | Interstitial loaded |
| 3a-i | Ad loaded successfully | — | ✅ | Ad shown → `EMI_Details_ACtivity` |
| 3a-ii | Ad **fails** to load | — | ⚠️ | `Load_Click()` → `EMI_Details_ACtivity` directly |
| 3b | Pro user OR cap not met | — | ⏭️ | `Load_Click()` → `EMI_Details_ACtivity` directly |
| 4 | **Reset** button tap | `calc_details_reset_clicked` | 🔄 | — |
| 4a | `resetButtonClickCount < threshold (2)` | — | 🔄 | `finish()` → back to EMI_Fragment |
| 4b | `resetButtonClickCount >= threshold` | — | 🔄 | `onBackPressed()` → interstitial on back |
| 5 | **Back navigation** | *(no event)* | — | `showInterstitialAd()` |
| 5a | Pro user | — | ⏭️ | `finish()` → back to EMI_Fragment |
| 5b | Cap not met | — | ⏭️ | `finish()` |
| 5c | Cap met AND ad loads | — | 💰 | Interstitial shown → `finish()` |
| 5d | Ad fails | — | ⚠️ | `finish()` |
| 6 | History icon tap | `emi_calculator_history_clicked` | ✅ | `HistoryList_Activity` |
| 7 | Share with Friends (shown after 5+ calculations) | *(no event)* | ✅ | System share intent |
| 8 | In-App Rating triggered | *(system — InAppRatingUtil)* | 🔔 | Google Play rating dialog |

---

## JOURNEY 6: Amortisation Table (EMI Details)

**Entry**: `EMI_Details_ACtivity` (from Calculate_Details_Activity "Details" button)
**File**: [`EMI_Details_ACtivity.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/Details/EMI_Details_ACtivity.java)

| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | Screen loads with amortisation schedule | *(no GA event)* | — | Table rendered |
| 2 | Back pressed | *(no GA event)* | 💀 | Returns to `Calculate_Details_Activity` |

---

## JOURNEY 7: History Screen

**Entry**: `HistoryList_Activity` (from EMI Fragment or Details screen)
**File**: [`HistoryList_Activity.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/History/)

| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | History list loads | *(no GA event)* | — | SQLite records displayed |
| 2 | Tap a history item | *(no GA event)* | ✅ | Details re-open with saved data |
| 3 | No history records | *(no GA event)* | ⚠️ empty | Empty state shown |

---

## JOURNEY 8: SIP Calculator

**File**: [`SPICalculatorFragment.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/navigationView/fragment/SPICalculatorFragment.java)

| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | Fragment loads | *(no open event)* | — | — |
| 2 | **Calculate** tapped | `sip_calculator_calculate_clicked` | ✅ | Result shown |
| 3 | **Reset** tapped | `sip_calculator_reset_clicked` | 🔄 | Fields cleared |

---

## JOURNEY 9: Settings

**Entry**: `Settings_Fragment` (from Drawer or language change restart)
**File**: [`Settings_Fragment.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/navigationView/fragment/Settings_Fragment.java)

| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | Settings screen opens | *(no open event)* | — | Preference list rendered |
| 2 | **Language** changed | `setting_language_selection` (with lang code as param) | 🔄 | Full app restart (`Main_Activity` recreated) |
| 3 | **Currency** changed | *(no GA event)* | 🔄 | Pref saved, summary updated |
| 4 | **Number Format** changed | *(no GA event)* | 🔄 | Pref saved |
| 5 | **Decimal Places** changed | *(no GA event)* | 🔄 | Pref saved |
| 6 | **Share** tapped | *(no GA event)* | ✅ | System share intent |
| 7 | **RevenueCat ID** tapped | *(no GA event)* | ✅ | Dialog with user ID + copy button |
| 8 | **Ad Inspector** (DEBUG only) | *(no GA event)* | 🛠️ debug | AdMob Inspector opens |
| 9 | **Version** entry | *(static, no event)* | — | Shows `versionName (versionCode)` |

---

## JOURNEY 10: News Flow

**Files**: [`EmiNewsFragment.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/news/EmiNewsFragment.java), [`EmiNewsAdapter.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/news/adapter/EmiNewsAdapter.java)

| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | News fragment appears in Home | `Home_news_viewed` | ✅ | Cards rendered |
| 2 | News card tapped | `Home_news_clicked` | ✅ | `News_Details_Activity` or `News_WebView_Activity` |
| 2a | Interstitial gate before news | 💰 | — | Ad shown then news |
| 3 | News share button tapped | `News_share_clicked` | ✅ | System share intent |
| 4 | View More News tapped | *(no event)* | ✅ | `EmiNews` activity |
| 5 | Network unavailable | *(no event)* | ⚠️ | Empty state / API failure silently ignored |

---

## JOURNEY 11: Info Page

**File**: [`Info_Fragment.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/navigationView/fragment/Info_Fragment.java)

| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | Social media link tapped | `info_page_socialmedia_clicked` | ✅ | External browser |
| 2 | Share App tapped | `info_page_share_App_clicked` | ✅ | Share intent |
| 3 | Rate Us tapped | `info_page_rate_us_clicked` | ✅ | Google Play store |
| 4 | Privacy Policy tapped | `info_page_privacy_policy_clicked` | ✅ | External browser |

---

## JOURNEY 12: Compare Loans

**Entry**: `Compare_Loan_Fragment` (Bottom nav "Loans" or Drawer)
**File**: [`Compare_Loan_Fragment.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/navigationView/fragment/Compare_Loan_Fragment.java)

| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | Fragment loads | *(no open event)* | — | Two loan inputs shown |
| 2 | Calculate comparison | *(no named GA event from grep)* | ✅ | Result table |

---

## JOURNEY 13: Currency Converter

**Entry**: `Currency_Fragment` (Drawer or Home V2)

| Step | State | Event | Branch | Next |
|------|-------|-------|--------|------|
| 1 | Fragment loads | *(no open event)* | — | Rate fetched |
| 1a | Currency converter opened via V2 home | `dashboard_currency_conv_clicked` | ✅ | Fragment shown |
| 2 | Network unavailable | *(no event)* | ⚠️ | Stale rates or error state |

---

## JOURNEY 14: Affiliate / Partner WebViews (Home Carousel)

**File**: [`ViewUtils.java`](emi_calc/app/src/main/java/com/finance/loan/emicalculator/utils/ViewUtils.java), Home carousel banner actions

| Tap | Event | Destination |
|-----|-------|-------------|
| Banner position 0 (IndiaLends) | `Analytics_Qureka_Web_Opened` + `"Indialends"` action | IndiaLends WebView |
| Banner position 1 (Quicko) | `Analytics_Qureka_Web_Opened` + `"Quicko"` action | Quicko WebView |
| Banner position 2 (Qureka) | `Analytics_Qureka_Web_Opened` + `"Qureka"` action | Qureka WebView |

---

## JOURNEY 15: System & Background Journeys

### 15.1 Push Notification (FCM)
| Trigger | Event | Branch | Next |
|---------|-------|--------|------|
| App open via notification | `check_data_from_bundle_data()` processes bundle | 🔔 | Routes to specific screen via `Notify_Type` |
| FCM topic subscribed on start | *(no GA event)* | 🔔 | Background |

### 15.2 Internal News Push Notification (WorkManager)
| Trigger | Event | Branch | Next |
|---------|-------|--------|------|
| Permission granted (Android 13+) | *(no GA event)* | 🔔 | `fetchNewsData()` + `scheduleOrCancelNewsWorker()` |
| Permission **denied** | *(no GA event)* | ⚠️ | Worker not scheduled |
| `internalNewsPNEnabled=false` | *(no GA event)* | ⏭️ | Worker cancelled |

### 15.3 In-App Update (Flexible)
| Trigger | Event | Branch | Next |
|---------|-------|--------|------|
| Update available | *(no GA event)* | 🔔 | Flexible update banner shown |

### 15.4 In-App Rating
| Trigger | Event | Branch | Next |
|---------|-------|--------|------|
| After successful calculation (Calculate_Details) | *(InAppRatingUtil auto-triggers)* | 🔔 | Google Play rating dialog |

### 15.5 CMP Consent (InMobi)
| Trigger | Event | Branch | Next |
|---------|-------|--------|------|
| First launch in EU/GDPR region | `showInMobi()` called if `connecttivityassistent_display_oneTime=true` | 🔔 | Consent dialog |

---

## COMPLETE EVENT REGISTRY

> All events by GA4 event name, source file, and journey reference.

| GA4 Event Name | Function Used | Source File | Journey |
|----------------|--------------|-------------|---------|
| `dashboard_viewed` | `LoggerEvent_for_Location` | `Main_Activity.java:444` | J3.1 |
| `footer_menu_home_clicked` | `set_FirebaseAnalytics_Events` | `Main_Activity.java:340` | J3.2 |
| `footer_menu_emi_cal_clicked` | `set_FirebaseAnalytics_Events` | `Main_Activity.java:359` | J3.2 |
| `footer_menu_compare_loan_clicked` | `set_FirebaseAnalytics_Events` | `Main_Activity.java:369` | J3.2 |
| `hm_emi_calculator_clicked` | `set_FirebaseAnalytics_Events` | `Main_Activity.java:482` | J3.3 |
| `hm_compare_loans_clicked` | `set_FirebaseAnalytics_Events` | `Main_Activity.java:493` | J3.3 |
| `hm_currency_conv_clicked` | `set_FirebaseAnalytics_Events` | `Main_Activity.java:541` | J3.3 |
| `hm_gst_cal_clicked` | `set_FirebaseAnalytics_Events` | `Main_Activity.java:550` | J3.3 |
| `hm_sip_cal_clicked` | `LoggerEvent_for_Location` | `Main_Activity.java:563` | J3.3 |
| `hm_fd_cal_clicked` | `set_FirebaseAnalytics_Events` | `Main_Activity.java:576` | J3.3 |
| `hm_rd_cal_clicked` | `set_FirebaseAnalytics_Events` | `Main_Activity.java:590` | J3.3 |
| `hm_ppf_cal_clicked` | `set_FirebaseAnalytics_Events` | `Main_Activity.java:604` | J3.3 |
| `setting_setting_clicked` | `LoggerEvent_for_Location` | `Main_Activity.java:527` | J3.3 |
| `hm_Join_whatsapp_clicked` | `set_FirebaseAnalytics_Events` | `Main_Activity.java:512` | J3.3 |
| `home_finance_see_all_clicked` | `set_FirebaseAnalytics_Events` | `Home_Fragment.java:445` | J3.4 |
| `Home_share_clicked` | `set_FirebaseAnalytics_Events` | `Home_Fragment.java:287,877` | J3.4 |
| `dashboard_currency_conv_clicked` | `LoggerEvent_for_Location` | `Home_Fragment.java:834` | J3.4 |
| `WebView_Calculator_CLICKED_<name>` | `set_FirebaseAnalytics_Events` | `Home_Fragment.java:518` | J3.4 |
| `WebView_Calculator_AD_COMPLETE_<name>` | `set_FirebaseAnalytics_Events` | `Home_Fragment.java:548` | J3.4 |
| `WebView_Calculator_NO_ADS_<name>` | `set_FirebaseAnalytics_Events` | `Home_Fragment.java:554` | J3.4 |
| `emi_calculator_emi_tab_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:1029,1064` | J4.1 |
| `emi_calculator_loan_amount_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:928` | J4.1 |
| `emi_calculator_interest_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:960` | J4.1 |
| `emi_calculator_period_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:993` | J4.1 |
| `emi_calculator_calculate_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:564` | J4.2 |
| `emi_calculator_loan_amt_cal_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:552` | J4.2 |
| `emi_calculator_interest_cal_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:556` | J4.2 |
| `emi_calculator_period_cal_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:560` | J4.2 |
| `new_design_calculate_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:543` | J4.2 (deprecated) |
| `emi_calculator_reset_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:489` | J4.3 |
| `emi_calculator_loan_amt_reset_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:483` | J4.3 |
| `emi_calculator_interest_reset_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:485` | J4.3 |
| `emi_calculator_period_reset_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:487` | J4.3 |
| `emi_calculator_history_clicked` | `LoggerEvent_for_Location` | `EMI_Fragment.java:447`, `Calculate_Details_Activity.java:223` | J4.4, J5.6 |
| `calc_details_reset_clicked` | `set_FirebaseAnalytics_Events` | `Calculate_Details_Activity.java:164` | J5.4 |
| `sip_calculator_calculate_clicked` | `LoggerEvent_for_Location` | `SPICalculatorFragment.java:371` | J8 |
| `sip_calculator_reset_clicked` | `LoggerEvent_for_Location` | `SPICalculatorFragment.java:325` | J8 |
| `setting_language_selection` | `LoggerEvent_for_Other` | `Settings_Fragment.java:667` | J9.2 |
| `Home_news_viewed` | `set_FirebaseAnalytics_Events` | `EmiNewsFragment.java:138` | J10.1 |
| `Home_news_clicked` | `set_FirebaseAnalytics_Events` | `EmiNewsAdapter.java:169` | J10.2 |
| `News_share_clicked` | `set_FirebaseAnalytics_Events` | `EmiNewsAdapter.java:188`, `SpecificGstNews.java:111` | J10.3 |
| `info_page_socialmedia_clicked` | `LoggerEvent_for_Location` | `Info_Fragment.java:172,190,204` | J11.1 |
| `info_page_share_App_clicked` | `LoggerEvent_for_Location` | `Info_Fragment.java:221` | J11.2 |
| `info_page_rate_us_clicked` | `LoggerEvent_for_Location` | `Info_Fragment.java:290` | J11.3 |
| `info_page_privacy_policy_clicked` | `LoggerEvent_for_Location` | `Info_Fragment.java:315` | J11.4 |
| `Analytics_Qureka_Web_Opened` | `set_FirebaseAnalytics_Events_forAffilates` | `ViewUtils.java:87,109,131` | J14 |

---

## REVENUE TOUCHPOINTS SUMMARY

| Touchpoint | Type | Trigger | Event Coverage |
|-----------|------|---------|---------------|
| Onboarding interstitial | Interstitial ad | After last onboarding slide (new users) | None — ad revenue only |
| Home banner | Banner ad (MEDIUM_RECT) | Home Fragment load | None |
| EMI Fragment banner | Banner ad (MEDIUM_RECT) | EMI_Fragment load | None |
| Calculate Details ad | Banner or Native (RC-controlled) | Calculate_Details open | None |
| WebView feature interstitial | Interstitial | Feature tile click (free users) | `WebView_Calculator_AD_COMPLETE_*` |
| Details → Amortisation gate | Interstitial | "Details" button (free users) | None |
| Back from Calculate Details | Interstitial | Back press (free users) | None |
| Reset from Calculate Details | Interstitial | Reset × 2+ (free users) | `calc_details_reset_clicked` |
| Paywall (RevenueCat) | Subscription | Premium icon / onboarding flow | None |
| Rewarded ad helper | Rewarded | `AdMobRewardedAdHelper` (not yet wired to a flow in current code) | None |
