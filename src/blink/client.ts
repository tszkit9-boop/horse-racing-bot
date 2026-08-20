import { createClient } from '@blinkdotnew/sdk'

export const blink = createClient({
  projectId: import.meta.env.VITE_BLINK_PROJECT_ID || 'telegram-bot-manager-z96ecdzq',
  publishableKey: import.meta.env.VITE_BLINK_PUBLISHABLE_KEY || 'blnk_pk_Ygvrii35mbVA_N_m-A36QYXpEyrDjElb',
  authRequired: false,
  auth: { mode: 'managed' },
})
