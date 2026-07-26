/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly PUBLIC_SITE_URL: string;
  readonly PUBLIC_GITHUB_URL: string;
  readonly PUBLIC_GITHUB_PROFILE_URL: string;
  readonly PUBLIC_LINKEDIN_URL: string;
  readonly PUBLIC_LICENSE_URL: string;
  readonly PUBLIC_NOTICE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
