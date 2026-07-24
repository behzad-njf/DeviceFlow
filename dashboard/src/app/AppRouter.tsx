import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './AppShell'
import { ProtectedRoute } from './ProtectedRoute'
import { LoginPage } from '../pages/Login/LoginPage'
import { OverviewPage } from '../pages/Overview/OverviewPage'
import { DevicesPage } from '../pages/Devices/DevicesPage'
import { MessagesPage } from '../pages/Messages/MessagesPage'
import { ProjectsPage } from '../pages/Projects/ProjectsPage'
import { LiveMonitorPage } from '../pages/LiveMonitor/LiveMonitorPage'
import { DeviceDetailPage } from '../pages/DeviceDetail/DeviceDetailPage'
import { QueuesPage } from '../pages/Queues/QueuesPage'
import { RoutingPage } from '../pages/Routing/RoutingPage'
import { ApiKeysPage } from '../pages/ApiKeys/ApiKeysPage'
import { WebhooksPage } from '../pages/Webhooks/WebhooksPage'
import { TemplatesPage } from '../pages/Templates/TemplatesPage'
import { PlaygroundPage } from '../pages/Playground/PlaygroundPage'
import { InboxPage } from '../pages/Inbox/InboxPage'
import { ContactsPage } from '../pages/Contacts/ContactsPage'
import { BulkPage } from '../pages/Bulk/BulkPage'
import { UsersPage } from '../pages/Users/UsersPage'
import { AuditPage } from '../pages/Audit/AuditPage'
import { AnalyticsPage } from '../pages/Analytics/AnalyticsPage'
import { MapPage } from '../pages/Map/MapPage'
import { PluginsPage } from '../pages/Plugins/PluginsPage'
import { NotificationsPage } from '../pages/Notifications/NotificationsPage'
import { AutomationsPage } from '../pages/Automations/AutomationsPage'

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route index element={<OverviewPage />} />
            <Route path="live" element={<LiveMonitorPage />} />
            <Route path="inbox" element={<InboxPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="map" element={<MapPage />} />
            <Route path="devices" element={<DevicesPage />} />
            <Route path="devices/:id" element={<DeviceDetailPage />} />
            <Route path="queues" element={<QueuesPage />} />
            <Route path="messages" element={<MessagesPage />} />
            <Route path="bulk" element={<BulkPage />} />
            <Route path="contacts" element={<ContactsPage />} />
            <Route path="projects" element={<ProjectsPage />} />
            <Route path="routing" element={<RoutingPage />} />
            <Route path="api-keys" element={<ApiKeysPage />} />
            <Route path="webhooks" element={<WebhooksPage />} />
            <Route path="automations" element={<AutomationsPage />} />
            <Route path="plugins" element={<PluginsPage />} />
            <Route path="notifications" element={<NotificationsPage />} />
            <Route path="templates" element={<TemplatesPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="audit" element={<AuditPage />} />
            <Route path="playground" element={<PlaygroundPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
