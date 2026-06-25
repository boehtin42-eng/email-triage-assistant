# Email Triage Assistant

ဒီ project သည် Streamlit web app ဖြစ်သည်။ App သည် unread emails များကိုသာ ဖတ်ပြီး triage result ထုတ်ပေးသည်။

## Safety rules

- Real business email ကို ပထမ test phase မှာ မသုံးပါ။
- Test Gmail account သို့မဟုတ် disposable mailbox ကိုသာ အရင်သုံးပါ။
- App သည် email မပို့ပါ။
- App သည် email မဖျက်ပါ။
- App သည် email ကို read အဖြစ် မပြောင်းပါ။
- App သည် external CRM ထဲမှာ data မပြောင်းပါ။

## Files

- `app.py` - Streamlit UI
- `triage_assistant.py` - Email, Gemini, Excel logic
- `requirements.txt` - Python packages
- `streamlit_secrets_example.toml` - Streamlit Secrets example

## Streamlit Secrets

Streamlit Community Cloud တွင် Settings > Secrets ထဲမှာ `streamlit_secrets_example.toml` ပုံစံအတိုင်း values ထည့်ပါ။

Local `.env` မသုံးပါ။

## Test order

1. Test Email
2. Test Gemini
3. Read Unread Emails and Create Draft Suggestions
4. Download Excel
5. Deploy test app
6. အားလုံးအောင်မြင်ပြီးမှ IONOS business mailbox ကို ပြင်ဆင်ပါ။

## Deployment outline

1. Code ကို GitHub repository ထဲသို့ push လုပ်ပါ။
2. Streamlit Community Cloud တွင် repository ကို connect လုပ်ပါ။
3. Main file ကို `app.py` ဟုရွေးပါ။
4. Settings > Secrets ထဲတွင် real values မဟုတ်သေးသော test mailbox values များကို အရင်ထည့်ပါ။
5. Deploy ပြီး app link ကိုဖွင့်ပါ။
6. Test Gmail mailbox ဖြင့် connection test နှင့် unread email triage ကို အရင်အောင်မြင်အောင်စစ်ပါ။
7. Business owner ထံ share မလုပ်ခင် test result ကို အတည်ပြုပါ။
8. နောက်ဆုံးမှသာ IONOS business mailbox secrets ကိုပြောင်းပါ။

## Local test note

Local test အတွက် `.streamlit/secrets.toml` ထဲမှာ dummy password ထည့်နိုင်သည်။ Real secrets မထည့်ပါနှင့်။ ထို file ကို `.gitignore` ထဲမှာ ထည့်ထားသည်။
