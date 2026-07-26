/** Site-wide constants. Override via PUBLIC_* env vars at build time. */

export const SITE_URL =
  import.meta.env.PUBLIC_SITE_URL || 'https://smsgateway.behzaaad.ir';

export const GITHUB_URL =
  import.meta.env.PUBLIC_GITHUB_URL || 'https://github.com/behzad-njf/DeviceFlow';

export const GITHUB_PROFILE_URL =
  import.meta.env.PUBLIC_GITHUB_PROFILE_URL || 'https://github.com/behzad-njf';

export const LINKEDIN_URL =
  import.meta.env.PUBLIC_LINKEDIN_URL || 'https://www.linkedin.com/in/behzadnjf/';

export const LICENSE_URL =
  import.meta.env.PUBLIC_LICENSE_URL ||
  'https://github.com/behzad-njf/DeviceFlow/blob/main/LICENSE';

export const NOTICE_URL =
  import.meta.env.PUBLIC_NOTICE_URL ||
  'https://github.com/behzad-njf/DeviceFlow/blob/main/NOTICE';

export const SITE_TITLE =
  'DeviceFlow — Self-hosted Android SMS Gateway & Device Automation';

export const SITE_DESCRIPTION =
  'Open-source, self-hosted SMS gateway. Turn Android phones into an API for OTP, transactional SMS, USSD, and fleet automation. Apache 2.0.';

export const SITE_NAME = 'DeviceFlow';
export const AUTHOR_NAME = 'Behzad';
export const COPYRIGHT_YEAR = 2026;
