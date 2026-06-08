@echo off
:: Redirect outputs to a daily log file to trace any issues
set LOG_FILE="c:\Yotta Work\Self Project\insta-automation\daily_run.log"
echo === Start Daily Run: %date% %time% === >> %LOG_FILE%

echo [1/2] Running Finance Agent...
cd /d "c:\Yotta Work\Self Project\insta-automation\finance_agent"
:: Run the finance agent script (change main.py or parameters if needed)
python main.py >> %LOG_FILE% 2>&1
echo Finance Agent Finished.

echo [2/2] Running UPSC Agent...
cd /d "c:\Yotta Work\Self Project\insta-automation\upsc_agent"
:: Run UPSC agent. It will query Telegram for your approval before publishing.
:: Note: If you want it to post immediately without Telegram gate, add --skip-approval.
python upsc_agent/main.py >> %LOG_FILE% 2>&1
echo UPSC Agent Finished.

echo === End Daily Run: %date% %time% === >> %LOG_FILE%
echo Log saved to %LOG_FILE%
