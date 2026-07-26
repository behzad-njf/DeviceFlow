export type FeatureId =
  | 'pairing'
  | 'otp'
  | 'transactional'
  | 'bulk'
  | 'fleet'
  | 'dualsim'
  | 'ussd'
  | 'webhooks'
  | 'contacts'
  | 'routing'
  | 'security'
  | 'dialer'
  | 'automations'
  | 'analytics';

export interface Feature {
  id: FeatureId;
  title: string;
  description: string;
}

export const features: Feature[] = [
  {
    id: 'pairing',
    title: 'Device pairing & heartbeat sync',
    description:
      'Pair phones with a short-lived code. Heartbeats keep battery, SIM, GPS, and online status fresh so the control plane always knows what’s live.',
  },
  {
    id: 'otp',
    title: 'OTP / login verification SMS',
    description:
      'Send one-time codes for signup and 2FA with mode: "otp". Real SIM routes, project scoping, and delivery status your auth stack can trust.',
  },
  {
    id: 'transactional',
    title: 'Transactional SMS',
    description:
      'Order confirmations, receipts, and account alerts through a REST API. Templates and project keys keep product messaging clean and auditable.',
  },
  {
    id: 'bulk',
    title: 'Bulk / marketing SMS',
    description:
      'Campaign send for announcements and outreach when you need volume—still self-hosted, still on your SIMs, with queue visibility in the dashboard.',
  },
  {
    id: 'fleet',
    title: 'Live device fleet monitor',
    description:
      'Watch online status, queues, battery, and dual-SIM health in real time over WebSockets. Ops sees the fleet the moment something drifts.',
  },
  {
    id: 'dualsim',
    title: 'Dual-SIM routing',
    description:
      'Route by SIM slot and operator. Keep failover paths ready when one carrier falters—ideal for multi-country or multi-operator fleets.',
  },
  {
    id: 'ussd',
    title: 'USSD from dashboard',
    description:
      'Run carrier USSD codes from the web UI. Balance checks, top-ups, and ops flows without touching the handset every time.',
  },
  {
    id: 'webhooks',
    title: 'Webhooks & project API keys',
    description:
      'Scoped API keys per project plus outbound webhooks for delivery and inbox events. Wire DeviceFlow into your backend without polling forever.',
  },
  {
    id: 'contacts',
    title: 'Contacts, inbox & conversations',
    description:
      'Import contacts, read inbound SMS, and follow conversation threads. Support and ops stay in one place with the devices that sent the messages.',
  },
  {
    id: 'routing',
    title: 'Smart routing / operator rules',
    description:
      'Prefer operators, SIM slots, and projects with rules that match how your fleet is deployed—less guesswork when a message has to land.',
  },
  {
    id: 'security',
    title: 'Hide launcher icon + passcode lock',
    description:
      'Agent app can hide from the launcher and require a UI passcode. Physical access to the phone does not mean open access to the agent.',
  },
  {
    id: 'dialer',
    title: 'Custom secret dialer code',
    description:
      'Reveal the agent with a dialer code like *#*#CODE#*#*. Field techs unlock the app without a visible launcher icon on the home screen.',
  },
  {
    id: 'automations',
    title: 'Automations & plugins',
    description:
      'Extend the control plane with automations and plugins. Trigger follow-ups, hooks, and custom logic when devices or messages change state.',
  },
  {
    id: 'analytics',
    title: 'Analytics, map & queues',
    description:
      'Ops views for send volume, GPS map pins from agents, and queue depth. See bottlenecks before they become outages.',
  },
];

export interface GuideStep {
  n: number;
  title: string;
  description: string;
  art: 'docker' | 'pair' | 'project' | 'send' | 'monitor';
}

export const guideSteps: GuideStep[] = [
  {
    n: 1,
    title: 'Run API + dashboard',
    description:
      'Start the Django API and React dashboard locally or with Docker Compose. Redis backs WebSockets and queues when you want the full ops stack.',
    art: 'docker',
  },
  {
    n: 2,
    title: 'Pair an Android phone',
    description:
      'Generate a pairing code in the dashboard. The Kotlin agent posts it once and receives a device token—no long-lived WebSocket required.',
    art: 'pair',
  },
  {
    n: 3,
    title: 'Attach device & create API key',
    description:
      'Assign the device to a project, then mint a project API key. Routing, templates, and webhooks all hang off that project boundary.',
    art: 'project',
  },
  {
    n: 4,
    title: 'Send OTP / SMS from your backend',
    description:
      'Call the REST API with mode: "otp" (or transactional / bulk). Your app stays the source of truth; DeviceFlow owns the SIM path.',
    art: 'send',
  },
  {
    n: 5,
    title: 'Monitor live status',
    description:
      'Watch heartbeats (~15s), command polls (~3s), queue depth, and delivery in Live Monitor. Fix fleet issues before users feel them.',
    art: 'monitor',
  },
];

export interface UseCase {
  id: string;
  title: string;
  description: string;
  art: 'auth' | 'commerce' | 'alerts' | 'ussd' | 'multisim' | 'selfhost';
}

export const useCases: UseCase[] = [
  {
    id: 'auth',
    title: 'Startup auth / 2FA OTP',
    description:
      'Ship login and verification codes on real SIMs you control—no per-message SaaS lock-in for your critical auth path.',
    art: 'auth',
  },
  {
    id: 'commerce',
    title: 'Marketplace & e-commerce SMS',
    description:
      'Order updates, shipping pings, and seller alerts from the same fleet that already handles OTP.',
    art: 'commerce',
  },
  {
    id: 'alerts',
    title: 'Internal ops alerts',
    description:
      'Page on-call or notify warehouse staff when queues spike, devices drop, or jobs fail—SMS that stays inside your infra.',
    art: 'alerts',
  },
  {
    id: 'ussd-ops',
    title: 'Carrier USSD automation',
    description:
      'Balance checks and carrier menus from the dashboard instead of walking every handset in the rack.',
    art: 'ussd',
  },
  {
    id: 'fleet',
    title: 'Multi-country dual-SIM fleet',
    description:
      'Run phones with local SIMs across regions. Route by operator and keep failover when one path degrades.',
    art: 'multisim',
  },
  {
    id: 'selfhost',
    title: 'Self-hosted vs pure SaaS SMS',
    description:
      'Keep numbers, logs, and routing under your roof. Open source under Apache 2.0 with clear attribution.',
    art: 'selfhost',
  },
];

export const trustItems = [
  'Apache 2.0',
  'Open source',
  'Self-hosted',
  'Django + React + Android',
] as const;

export const whyItems = [
  {
    title: 'Self-hosted control',
    description:
      'Your phones, your Postgres, your Redis. Deploy on hardware you trust and keep message paths inside your boundary.',
  },
  {
    title: 'Real SIM routes',
    description:
      'OTP and transactional SMS leave through physical SIMs—not a black-box SaaS number pool you cannot audit.',
  },
  {
    title: 'API-first',
    description:
      'REST for send and ops, WebSockets for live UI, OpenAPI for discoverability. Build products on DeviceFlow, not around a click-only console.',
  },
  {
    title: 'Attribution-friendly license',
    description:
      'Apache 2.0 plus a clear NOTICE: use it, fork it, ship it—credit the DeviceFlow GitHub repo.',
  },
] as const;
