import { useEffect, useState } from 'react';
import {
  Shield, Lock, Unlock, Mail, Plus, Trash2, Save, Eye, EyeOff,
  Brain, Clock, FolderOpen, Cloud, ExternalLink, Link2, KeyRound,
  ListFilter, Globe, Wifi, ChevronDown, ChevronUp, ToggleLeft, ToggleRight,
} from 'lucide-react';
import {
  getStatus, setupMasterPassword, unlock as apiUnlock, lock as apiLock,
  getAccounts, addAccount, updateAccount, deleteAccount, storeCredentials, getConfig, updateConfig,
  getCloudProviders, getCloudConnections, createCloudConnection, deleteCloudConnection,
  startOAuth2Flow, getEmailProviders,
  getRules, createRule, updateRule, deleteRule, getRuleFields,
  getCloudMode, refreshAllAttachments, refreshAllStatus,
} from '../lib/api';

export default function SettingsPage() {
  const [initialized, setInitialized] = useState(false);
  const [unlocked, setUnlocked] = useState(false);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [config, setConfig] = useState<any>(null);
  const [tab, setTab] = useState('security');
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [refreshingAll, setRefreshingAll] = useState(false);

  // New account form
  const [newAccount, setNewAccount] = useState({
    name: '', email: '', provider: 'gmail', auth_method: 'app_password',
    imap_server: '', imap_port: 993, poll_interval_minutes: 15,
    folders: ['INBOX'], download_invoice_links: true,
    search_criteria: 'UNSEEN', only_with_attachments: false,
    max_emails_per_fetch: 50, skip_older_than_days: 0,
    start_ingest_date: '',
    post_action: 'none', post_action_folder: '',
  });
  const [appPassword, setAppPassword] = useState('');
  const [showAddAccount, setShowAddAccount] = useState(false);
  const [editingAccount, setEditingAccount] = useState<string | null>(null);
  const [editAccount, setEditAccount] = useState<any>(null);

  // Cloud storage
  const [cloudProviders, setCloudProviders] = useState<any[]>([]);
  const [cloudConnections, setCloudConnections] = useState<any[]>([]);
  const [emailProviders, setEmailProviders] = useState<any[]>([]);

  // Email rules
  const [rules, setRules] = useState<any[]>([]);
  const [ruleFields, setRuleFields] = useState<any>(null);
  const [showAddRule, setShowAddRule] = useState(false);
  const [expandedRule, setExpandedRule] = useState<number | null>(null);
  const [newRule, setNewRule] = useState({
    name: '', priority: 5, enabled: true,
    conditions: [{ field: 'subject', operator: 'contains', value: '' }],
    actions: [{ action: 'label', value: '' }],
  });

  // Cloud mode
  const [cloudModeInfo, setCloudModeInfo] = useState<any>(null);

  const loadStatus = async () => {
    try {
      const resp = await getStatus();
      setInitialized(resp.data.initialized);
      setUnlocked(resp.data.unlocked);
    } catch { /* API not available */ }
    setLoading(false);
  };

  const loadAccounts = async () => {
    try {
      const resp = await getAccounts();
      setAccounts(resp.data.accounts || []);
    } catch { /* ignore */ }
  };

  const loadConfig = async () => {
    try {
      const resp = await getConfig();
      setConfig(resp.data);
    } catch { /* ignore */ }
  };

  const loadCloudData = async () => {
    try {
      const [provResp, connResp, emailProvResp] = await Promise.all([
        getCloudProviders(),
        getCloudConnections(),
        getEmailProviders(),
      ]);
      setCloudProviders(provResp.data.providers || []);
      setCloudConnections(connResp.data.connections || []);
      setEmailProviders(emailProvResp.data.providers || []);
    } catch { /* ignore */ }
  };

  const loadRules = async () => {
    try {
      const [rulesResp, fieldsResp] = await Promise.all([getRules(), getRuleFields()]);
      setRules(rulesResp.data.rules || []);
      setRuleFields(fieldsResp.data);
    } catch { /* ignore */ }
  };

  const loadCloudMode = async () => {
    try {
      const resp = await getCloudMode();
      setCloudModeInfo(resp.data);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    loadStatus();
    loadAccounts();
    loadConfig();
    loadCloudData();
    loadRules();
    loadCloudMode();
  }, []);

  const handleConnectCloud = async (provider: string) => {
    try {
      // Create the connection record
      await createCloudConnection({ provider });
      // Start OAuth2 flow
      const resp = await startOAuth2Flow({
        flow_type: 'cloud_storage',
        provider,
      });
      // Open OAuth consent in new window
      window.open(resp.data.url, '_blank', 'width=600,height=700');
      setMessage('Complete authorization in the popup window, then refresh.');
      // Reload connections after a delay
      setTimeout(() => loadCloudData(), 5000);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Failed to start cloud connection';
      setMessage(detail);
    }
  };

  const handleConnectEmail = async (provider: string) => {
    try {
      const resp = await startOAuth2Flow({
        flow_type: 'email',
        provider,
      });
      window.open(resp.data.url, '_blank', 'width=600,height=700');
      setMessage('Complete authorization in the popup window.');
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Failed to start email connection';
      setMessage(detail);
    }
  };

  const handleDeleteCloud = async (id: string) => {
    try {
      await deleteCloudConnection(id);
      setMessage('Cloud connection removed');
      loadCloudData();
    } catch { /* ignore */ }
  };

  const handleSetup = async () => {
    if (!password) return;
    try {
      if (initialized) {
        await apiUnlock(password);
        setMessage('Unlocked successfully');
      } else {
        await setupMasterPassword(password);
        setMessage('Master password set successfully');
      }
      setUnlocked(true);
      setPassword('');
      loadAccounts();
    } catch {
      setMessage('Invalid password');
    }
  };

  const handleLock = async () => {
    try {
      await apiLock();
      setUnlocked(false);
      setMessage('Locked');
    } catch { /* ignore */ }
  };

  const handleAddAccount = async () => {
    // If user provided a password, credential store must be unlocked first
    if (appPassword && !unlocked) {
      setMessage(initialized
        ? 'Please unlock the credential store first (Security tab) before adding credentials.'
        : 'Please set up a master password first (Security tab) before adding credentials.'
      );
      return;
    }

    try {
      const resp = await addAccount(newAccount);
      const accountId = resp.data.account_id;

      if (appPassword && unlocked) {
        try {
          await storeCredentials(accountId, {
            account_id: accountId,
            app_password: appPassword,
          });
        } catch {
          setMessage('Account added but failed to store credentials — is the credential store unlocked?');
          loadAccounts();
          return;
        }
      }

      setShowAddAccount(false);
      setNewAccount({
        name: '', email: '', provider: 'gmail', auth_method: 'app_password',
        imap_server: '', imap_port: 993, poll_interval_minutes: 15,
        folders: ['INBOX'], download_invoice_links: true,
        search_criteria: 'UNSEEN', only_with_attachments: false,
        max_emails_per_fetch: 50, skip_older_than_days: 0,
        start_ingest_date: '',
        post_action: 'none', post_action_folder: '',
      });
      setAppPassword('');
      setMessage('Account added successfully');
      loadAccounts();
    } catch {
      setMessage('Failed to add account');
    }
  };

  const handleDeleteAccount = async (id: string) => {
    try {
      await deleteAccount(id);
      setMessage('Account deleted');
      loadAccounts();
    } catch { /* ignore */ }
  };

  const handleSaveConfig = async () => {
    if (!config) return;
    try {
      await updateConfig(config);
      setMessage('Configuration saved');
    } catch {
      setMessage('Failed to save configuration');
    }
  };

  const handleCreateRule = async () => {
    try {
      await createRule(newRule);
      setShowAddRule(false);
      setNewRule({
        name: '', priority: 5, enabled: true,
        conditions: [{ field: 'subject', operator: 'contains', value: '' }],
        actions: [{ action: 'label', value: '' }],
      });
      setMessage('Rule created');
      loadRules();
    } catch { setMessage('Failed to create rule'); }
  };

  const handleToggleRule = async (rule: any) => {
    try {
      await updateRule(rule.id, { enabled: !rule.enabled });
      loadRules();
    } catch { /* ignore */ }
  };

  const handleDeleteRule = async (id: number) => {
    try {
      await deleteRule(id);
      setMessage('Rule deleted');
      loadRules();
    } catch { /* ignore */ }
  };

  const tabs = [
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'accounts', label: 'Email Accounts', icon: Mail },
    { id: 'rules', label: 'Email Rules', icon: ListFilter },
    { id: 'oauth', label: 'OAuth Providers', icon: KeyRound },
    { id: 'cloud', label: 'Cloud Storage', icon: Cloud },
    { id: 'cloudmode', label: 'Cloud Mode', icon: Globe },
    { id: 'llm', label: 'LLM / AI', icon: Brain },
    { id: 'storage', label: 'Storage', icon: FolderOpen },
    { id: 'scheduler', label: 'Scheduler', icon: Clock },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-sunset-400 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-warm-900">Settings</h2>
        <p className="text-sm text-sand-600 mt-0.5">Configure Regia to your needs</p>
      </div>

      {message && (
        <div className="px-4 py-2.5 bg-sunset-100 border border-sunset-200 rounded-xl text-sm text-sunset-800 flex items-center justify-between">
          <span>{message}</span>
          <button onClick={() => setMessage('')} className="text-sunset-500 hover:text-sunset-700 text-xs ml-4">Dismiss</button>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-1 bg-sand-100 p-1 rounded-xl w-fit">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-colors ${
              tab === t.id ? 'bg-white text-warm-900 shadow-sm' : 'text-sand-600 hover:text-warm-700'
            }`}
          >
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-2xl border border-sand-200 shadow-sm p-6">
        {/* === Security Tab === */}
        {tab === 'security' && (
          <div className="space-y-6 max-w-md">
            <div>
              <h3 className="text-lg font-semibold text-warm-900 flex items-center gap-2">
                <Shield className="w-5 h-5 text-sunset-500" /> Master Password
              </h3>
              <p className="text-sm text-sand-500 mt-1">
                {initialized
                  ? 'Your credential store is encrypted. Enter your password to unlock.'
                  : 'Set a master password to encrypt your email credentials.'
                }
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
                unlocked ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}>
                {unlocked ? <Unlock className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
                {unlocked ? 'Unlocked' : 'Locked'}
              </span>
            </div>

            {!unlocked ? (
              <div className="space-y-3">
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={initialized ? 'Enter master password' : 'Create master password'}
                    className="w-full px-4 py-2.5 bg-sand-50 border border-sand-200 rounded-xl text-sm
                               focus:outline-none focus:ring-2 focus:ring-sunset-400/40 focus:border-sunset-400"
                    onKeyDown={(e) => e.key === 'Enter' && handleSetup()}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-sand-400 hover:text-warm-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <button
                  onClick={handleSetup}
                  className="px-5 py-2.5 bg-gradient-to-r from-sunset-500 to-sunset-600 text-white rounded-xl
                             text-sm font-medium shadow-sm hover:shadow-md transition-all"
                >
                  {initialized ? 'Unlock' : 'Set Password'}
                </button>
              </div>
            ) : (
              <button
                onClick={handleLock}
                className="px-5 py-2.5 bg-sand-100 text-warm-700 rounded-xl text-sm font-medium hover:bg-sand-200 transition-colors"
              >
                Lock Credential Store
              </button>
            )}

            {/* Refresh all attachments */}
            <div className="pt-2">
              <p className="text-sm text-warm-900 font-semibold mb-2">Attachment Refresh</p>
              <p className="text-xs text-sand-500 mb-2">Ensure all attachments are written to disk in the original ingestion paths.</p>
              <button
                onClick={async () => {
                  setRefreshingAll(true);
                  setMessage('Starting background refresh...');
                  try {
                    const resp = await refreshAllAttachments();
                    const d = resp.data;
                    if (d.status === 'already_running') {
                      setMessage(`Refresh already running: ${d.processed}/${d.total} done`);
                    } else {
                      setMessage(`Refresh started for ${d.total} emails — runs in background`);
                    }
                    // Poll status every 3s
                    const poll = setInterval(async () => {
                      try {
                        const s = (await refreshAllStatus()).data;
                        setMessage(`Refreshing: ${s.processed}/${s.total} done, ${s.errors?.length || 0} errors`);
                        if (!s.running) {
                          clearInterval(poll);
                          setRefreshingAll(false);
                          setMessage(`Refresh complete: ${s.processed}/${s.total} processed, ${s.errors?.length || 0} errors`);
                        }
                      } catch {
                        clearInterval(poll);
                        setRefreshingAll(false);
                      }
                    }, 3000);
                  } catch {
                    setMessage('Failed to start refresh');
                    setRefreshingAll(false);
                  }
                }}
                disabled={refreshingAll}
                className="px-4 py-2 rounded-lg text-xs font-medium bg-sand-100 text-sand-700 hover:bg-sand-200 disabled:opacity-50"
              >
                {refreshingAll ? 'Refreshing...' : 'Refresh all attachments'}
              </button>
            </div>
          </div>
        )}

        {/* === Accounts Tab === */}
        {tab === 'accounts' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-warm-900">Email Accounts</h3>
              <button
                onClick={() => setShowAddAccount(!showAddAccount)}
                className="flex items-center gap-1.5 px-3 py-2 bg-sunset-500 text-white rounded-xl text-xs font-medium hover:bg-sunset-600 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" /> Add Account
              </button>
            </div>

            {/* Add Account Form */}
            {showAddAccount && (
              <div className="bg-sand-50 rounded-xl p-4 border border-sand-200 space-y-4">
                {!unlocked && (
                  <div className="flex items-center gap-2 px-3 py-2 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-700">
                    <Shield className="w-4 h-4 shrink-0" />
                    {initialized
                      ? 'Credential store is locked. Unlock it in the Security tab to save passwords.'
                      : 'Set up a master password in the Security tab first to save credentials securely.'}
                  </div>
                )}

                {/* Connection */}
                <div>
                  <h4 className="text-xs font-semibold text-warm-800 mb-2">Connection</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium text-sand-600 mb-1 block">Name</label>
                      <input type="text" placeholder="My Gmail" value={newAccount.name}
                        onChange={e => setNewAccount({...newAccount, name: e.target.value})}
                        className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-sand-600 mb-1 block">Email</label>
                      <input type="email" placeholder="user@gmail.com" value={newAccount.email}
                        onChange={e => setNewAccount({...newAccount, email: e.target.value})}
                        className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-sand-600 mb-1 block">Provider</label>
                      <select value={newAccount.provider} onChange={e => setNewAccount({...newAccount, provider: e.target.value})}
                        className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40">
                        <option value="gmail">Gmail</option>
                        <option value="outlook">Outlook</option>
                        <option value="imap">Custom IMAP</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-sand-600 mb-1 block">App Password</label>
                      <input type="password" placeholder="App-specific password" value={appPassword}
                        onChange={e => setAppPassword(e.target.value)}
                        className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                    </div>
                  </div>
                </div>

                {/* Polling */}
                <div>
                  <h4 className="text-xs font-semibold text-warm-800 mb-2">Polling & Filtering</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium text-sand-600 mb-1 block">Folders</label>
                      <input type="text" placeholder="INBOX" value={newAccount.folders.join(', ')}
                        onChange={e => setNewAccount({...newAccount, folders: e.target.value.split(',').map(s => s.trim()).filter(Boolean)})}
                        className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                      <p className="text-[10px] text-sand-400 mt-0.5">Comma-separated folder names</p>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-sand-600 mb-1 block">Poll Interval (min)</label>
                      <input type="number" min={1} max={1440} value={newAccount.poll_interval_minutes}
                        onChange={e => setNewAccount({...newAccount, poll_interval_minutes: parseInt(e.target.value) || 15})}
                        className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-sand-600 mb-1 block">Search Criteria</label>
                      <select value={newAccount.search_criteria}
                        onChange={e => setNewAccount({...newAccount, search_criteria: e.target.value})}
                        className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40">
                        <option value="UNSEEN">Unread only</option>
                        <option value="ALL">All emails</option>
                        <option value="SEEN">Read only</option>
                        <option value="FLAGGED">Starred / flagged</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-sand-600 mb-1 block">Max Emails per Fetch</label>
                      <input type="number" min={0} max={500} value={newAccount.max_emails_per_fetch}
                        onChange={e => setNewAccount({...newAccount, max_emails_per_fetch: parseInt(e.target.value) || 0})}
                        className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                      <p className="text-[10px] text-sand-400 mt-0.5">0 = unlimited</p>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-sand-600 mb-1 block">Skip Older Than (days)</label>
                      <input type="number" min={0} value={newAccount.skip_older_than_days}
                        onChange={e => setNewAccount({...newAccount, skip_older_than_days: parseInt(e.target.value) || 0})}
                        className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                      <p className="text-[10px] text-sand-400 mt-0.5">0 = no age limit</p>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-sand-600 mb-1 block">Start Ingest Date</label>
                      <input type="date" value={newAccount.start_ingest_date}
                        onChange={e => setNewAccount({...newAccount, start_ingest_date: e.target.value})}
                        className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                      <p className="text-[10px] text-sand-400 mt-0.5">Only ingest emails from this date onward (overrides days limit)</p>
                    </div>
                    <div className="flex items-center gap-2 pt-5">
                      <input type="checkbox" id="only_attachments" checked={newAccount.only_with_attachments}
                        onChange={e => setNewAccount({...newAccount, only_with_attachments: e.target.checked})}
                        className="rounded border-sand-300" />
                      <label htmlFor="only_attachments" className="text-xs text-sand-600">Only emails with attachments</label>
                    </div>
                  </div>
                </div>

                {/* Post-Processing */}
                <div>
                  <h4 className="text-xs font-semibold text-warm-800 mb-2">After Ingestion</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium text-sand-600 mb-1 block">Post-Processing Action</label>
                      <select value={newAccount.post_action}
                        onChange={e => setNewAccount({...newAccount, post_action: e.target.value})}
                        className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40">
                        <option value="none">Leave as-is (read-only)</option>
                        <option value="mark_read">Mark as read</option>
                        <option value="move">Move to folder</option>
                        <option value="archive">Archive</option>
                        <option value="delete">Delete from server</option>
                      </select>
                    </div>
                    {newAccount.post_action === 'move' && (
                      <div>
                        <label className="text-xs font-medium text-sand-600 mb-1 block">Move To Folder</label>
                        <input type="text" placeholder="Processed" value={newAccount.post_action_folder}
                          onChange={e => setNewAccount({...newAccount, post_action_folder: e.target.value})}
                          className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                      </div>
                    )}
                    <div className="flex items-center gap-2 pt-5">
                      <input type="checkbox" id="dl_invoices" checked={newAccount.download_invoice_links}
                        onChange={e => setNewAccount({...newAccount, download_invoice_links: e.target.checked})}
                        className="rounded border-sand-300" />
                      <label htmlFor="dl_invoices" className="text-xs text-sand-600">Download invoice links from emails</label>
                    </div>
                  </div>
                  {newAccount.post_action === 'delete' && (
                    <div className="flex items-center gap-2 mt-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">
                      <Trash2 className="w-3.5 h-3.5 shrink-0" /> Emails will be permanently deleted from the server after ingestion.
                    </div>
                  )}
                </div>

                <div className="flex gap-2 pt-1">
                  <button onClick={handleAddAccount}
                    className="px-4 py-2 bg-sunset-500 text-white rounded-lg text-xs font-medium hover:bg-sunset-600 transition-colors">
                    Save Account
                  </button>
                  <button onClick={() => setShowAddAccount(false)}
                    className="px-4 py-2 bg-sand-100 text-sand-600 rounded-lg text-xs font-medium hover:bg-sand-200 transition-colors">
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Account List */}
            {accounts.length === 0 ? (
              <div className="text-center py-8 text-sand-400">
                <Mail className="w-10 h-10 mx-auto mb-2 text-sand-300" />
                <p className="text-sm">No email accounts configured</p>
              </div>
            ) : (
              <div className="space-y-2">
                {accounts.map((acc: any) => (
                  <div key={acc.id} className="bg-sand-50 rounded-xl border border-sand-200 overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-sunset-100 flex items-center justify-center">
                          <Mail className="w-4 h-4 text-sunset-500" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-warm-900">{acc.name || acc.email}</p>
                          <p className="text-[11px] text-sand-500">
                            {acc.email} · {acc.provider} · {acc.search_criteria || 'UNSEEN'} · every {acc.poll_interval_minutes}m
                            {acc.post_action && acc.post_action !== 'none' && ` · ${acc.post_action}`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                          acc.enabled ? 'bg-green-100 text-green-700' : 'bg-sand-200 text-sand-500'
                        }`}>
                          {acc.enabled ? 'Active' : 'Disabled'}
                        </span>
                        <button onClick={() => { setEditingAccount(editingAccount === acc.id ? null : acc.id); setEditAccount({...acc}); }}
                          className="p-1.5 rounded-lg hover:bg-sand-200 text-sand-400 hover:text-warm-600 transition-colors" title="Edit">
                          <ChevronDown className={`w-4 h-4 transition-transform ${editingAccount === acc.id ? 'rotate-180' : ''}`} />
                        </button>
                        <button onClick={() => handleDeleteAccount(acc.id)}
                          className="p-1.5 rounded-lg hover:bg-red-100 text-sand-400 hover:text-red-500 transition-colors" title="Delete">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Inline Edit Panel */}
                    {editingAccount === acc.id && editAccount && (
                      <div className="px-4 pb-4 pt-1 border-t border-sand-200 space-y-3">
                        <div className="grid grid-cols-3 gap-3">
                          <div>
                            <label className="text-[10px] font-medium text-sand-500 mb-0.5 block">Folders</label>
                            <input type="text" value={(editAccount.folders || []).join(', ')}
                              onChange={e => setEditAccount({...editAccount, folders: e.target.value.split(',').map((s: string) => s.trim()).filter(Boolean)})}
                              className="w-full px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                          </div>
                          <div>
                            <label className="text-[10px] font-medium text-sand-500 mb-0.5 block">Poll (min)</label>
                            <input type="number" min={1} max={1440} value={editAccount.poll_interval_minutes || 15}
                              onChange={e => setEditAccount({...editAccount, poll_interval_minutes: parseInt(e.target.value) || 15})}
                              className="w-full px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                          </div>
                          <div>
                            <label className="text-[10px] font-medium text-sand-500 mb-0.5 block">Search</label>
                            <select value={editAccount.search_criteria || 'UNSEEN'}
                              onChange={e => setEditAccount({...editAccount, search_criteria: e.target.value})}
                              className="w-full px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40">
                              <option value="UNSEEN">Unread only</option>
                              <option value="ALL">All emails</option>
                              <option value="SEEN">Read only</option>
                              <option value="FLAGGED">Starred / flagged</option>
                            </select>
                          </div>
                          <div>
                            <label className="text-[10px] font-medium text-sand-500 mb-0.5 block">Max per Fetch</label>
                            <input type="number" min={0} max={500} value={editAccount.max_emails_per_fetch || 0}
                              onChange={e => setEditAccount({...editAccount, max_emails_per_fetch: parseInt(e.target.value) || 0})}
                              className="w-full px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                          </div>
                          <div>
                            <label className="text-[10px] font-medium text-sand-500 mb-0.5 block">Skip Older (days)</label>
                            <input type="number" min={0} value={editAccount.skip_older_than_days || 0}
                              onChange={e => setEditAccount({...editAccount, skip_older_than_days: parseInt(e.target.value) || 0})}
                              className="w-full px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                          </div>
                          <div>
                            <label className="text-[10px] font-medium text-sand-500 mb-0.5 block">Start Ingest Date</label>
                            <input type="date" value={editAccount.start_ingest_date || ''}
                              onChange={e => setEditAccount({...editAccount, start_ingest_date: e.target.value})}
                              className="w-full px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                          </div>
                          <div>
                            <label className="text-[10px] font-medium text-sand-500 mb-0.5 block">Post Action</label>
                            <select value={editAccount.post_action || 'none'}
                              onChange={e => setEditAccount({...editAccount, post_action: e.target.value})}
                              className="w-full px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40">
                              <option value="none">Leave as-is</option>
                              <option value="mark_read">Mark read</option>
                              <option value="move">Move to folder</option>
                              <option value="archive">Archive</option>
                              <option value="delete">Delete</option>
                            </select>
                          </div>
                        </div>
                        {editAccount.post_action === 'move' && (
                          <div className="max-w-xs">
                            <label className="text-[10px] font-medium text-sand-500 mb-0.5 block">Move To Folder</label>
                            <input type="text" placeholder="Processed" value={editAccount.post_action_folder || ''}
                              onChange={e => setEditAccount({...editAccount, post_action_folder: e.target.value})}
                              className="w-full px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                          </div>
                        )}
                        <div className="flex items-center gap-4">
                          <label className="flex items-center gap-1.5 text-xs text-sand-600">
                            <input type="checkbox" checked={editAccount.only_with_attachments || false}
                              onChange={e => setEditAccount({...editAccount, only_with_attachments: e.target.checked})}
                              className="rounded border-sand-300" /> Attachments only
                          </label>
                          <label className="flex items-center gap-1.5 text-xs text-sand-600">
                            <input type="checkbox" checked={editAccount.download_invoice_links !== false}
                              onChange={e => setEditAccount({...editAccount, download_invoice_links: e.target.checked})}
                              className="rounded border-sand-300" /> Download invoice links
                          </label>
                          <label className="flex items-center gap-1.5 text-xs text-sand-600">
                            <input type="checkbox" checked={editAccount.enabled !== false}
                              onChange={e => setEditAccount({...editAccount, enabled: e.target.checked})}
                              className="rounded border-sand-300" /> Enabled
                          </label>
                        </div>
                        <div className="flex gap-2">
                          <button onClick={async () => {
                            try {
                              await updateAccount(acc.id, editAccount);
                              setMessage('Account updated'); setEditingAccount(null); loadAccounts();
                            } catch { setMessage('Failed to update account'); }
                          }}
                            className="px-3 py-1.5 bg-sunset-500 text-white rounded-lg text-xs font-medium hover:bg-sunset-600 transition-colors">
                            <Save className="w-3.5 h-3.5 inline mr-1" />Save Changes
                          </button>
                          <button onClick={() => setEditingAccount(null)}
                            className="px-3 py-1.5 bg-sand-100 text-sand-600 rounded-lg text-xs font-medium hover:bg-sand-200 transition-colors">
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* === OAuth Providers Tab === */}
        {tab === 'oauth' && config && (
          <div className="space-y-6 max-w-lg">
            <div>
              <h3 className="text-lg font-semibold text-warm-900 flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-sunset-500" /> OAuth Provider Credentials
              </h3>
              <p className="text-xs text-sand-500 mt-1">
                Required for "Connect with Google/Microsoft" buttons. Create OAuth credentials in
                your provider's developer console and enter them here.
              </p>
            </div>

            {/* Google */}
            <div className="space-y-3 p-4 bg-sand-50 rounded-xl border border-sand-200">
              <h4 className="text-sm font-semibold text-warm-900 flex items-center gap-2">
                <ExternalLink className="w-4 h-4" /> Google (Gmail & Drive)
              </h4>
              <p className="text-[11px] text-sand-400">
                Create credentials at{' '}
                <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noreferrer"
                  className="text-sunset-500 underline">console.cloud.google.com</a>.
                Set redirect URI to: <code className="bg-sand-200 px-1 rounded text-[10px]">http://localhost:8420/api/oauth2/callback</code>
              </p>
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Client ID</label>
                <input
                  type="text" placeholder="xxxx.apps.googleusercontent.com"
                  value={config.oauth_providers?.google_client_id || ''}
                  onChange={e => setConfig({...config, oauth_providers: {...(config.oauth_providers || {}), google_client_id: e.target.value}})}
                  className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Client Secret</label>
                <input
                  type="password" placeholder="GOCSPX-..."
                  value={config.oauth_providers?.google_client_secret || ''}
                  onChange={e => setConfig({...config, oauth_providers: {...(config.oauth_providers || {}), google_client_secret: e.target.value}})}
                  className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
              </div>
            </div>

            {/* Microsoft */}
            <div className="space-y-3 p-4 bg-sand-50 rounded-xl border border-sand-200">
              <h4 className="text-sm font-semibold text-warm-900 flex items-center gap-2">
                <ExternalLink className="w-4 h-4" /> Microsoft (Outlook & OneDrive)
              </h4>
              <p className="text-[11px] text-sand-400">
                Create credentials at{' '}
                <a href="https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps" target="_blank" rel="noreferrer"
                  className="text-sunset-500 underline">Azure Portal</a>.
                Set redirect URI to: <code className="bg-sand-200 px-1 rounded text-[10px]">http://localhost:8420/api/oauth2/callback</code>
              </p>
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Client ID (Application ID)</label>
                <input
                  type="text" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  value={config.oauth_providers?.microsoft_client_id || ''}
                  onChange={e => setConfig({...config, oauth_providers: {...(config.oauth_providers || {}), microsoft_client_id: e.target.value}})}
                  className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Client Secret</label>
                <input
                  type="password" placeholder="Client secret value"
                  value={config.oauth_providers?.microsoft_client_secret || ''}
                  onChange={e => setConfig({...config, oauth_providers: {...(config.oauth_providers || {}), microsoft_client_secret: e.target.value}})}
                  className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
              </div>
            </div>

            <button onClick={handleSaveConfig}
              className="flex items-center gap-2 px-4 py-2 bg-sunset-500 text-white rounded-lg text-xs font-medium hover:bg-sunset-600 transition-colors">
              <Save className="w-4 h-4" /> Save OAuth Credentials
            </button>
          </div>
        )}

        {/* === LLM Tab === */}
        {tab === 'llm' && config && (
          <div className="space-y-4 max-w-lg">
            <h3 className="text-lg font-semibold text-warm-900 flex items-center gap-2">
              <Brain className="w-5 h-5 text-sunset-500" /> LLM Configuration
            </h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Model Name</label>
                <input
                  type="text"
                  value={config.llm?.model_name || ''}
                  onChange={e => setConfig({...config, llm: {...config.llm, model_name: e.target.value}})}
                  className="w-full px-3 py-2 bg-sand-50 border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
                <p className="text-[11px] text-sand-400 mt-1">Recommended: qwen2.5:0.5b (ultra-light), tinyllama, phi</p>
              </div>
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Ollama URL</label>
                <input
                  type="text"
                  value={config.llm?.ollama_base_url || ''}
                  onChange={e => setConfig({...config, llm: {...config.llm, ollama_base_url: e.target.value}})}
                  className="w-full px-3 py-2 bg-sand-50 border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={config.llm?.fallback_to_rules ?? true}
                  onChange={e => setConfig({...config, llm: {...config.llm, fallback_to_rules: e.target.checked}})}
                  className="rounded border-sand-300 text-sunset-500 focus:ring-sunset-400"
                />
                <label className="text-sm text-warm-700">Fallback to rule-based classification if LLM unavailable</label>
              </div>
            </div>
            <button onClick={handleSaveConfig}
              className="flex items-center gap-2 px-4 py-2 bg-sunset-500 text-white rounded-xl text-sm font-medium hover:bg-sunset-600 transition-colors">
              <Save className="w-4 h-4" /> Save Configuration
            </button>
          </div>
        )}

        {/* === Storage Tab === */}
        {tab === 'storage' && config && (
          <div className="space-y-4 max-w-lg">
            <h3 className="text-lg font-semibold text-warm-900 flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-sunset-500" /> Storage Configuration
            </h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Storage Directory</label>
                <input
                  type="text"
                  value={config.storage?.base_dir || ''}
                  onChange={e => setConfig({...config, storage: {...config.storage, base_dir: e.target.value}})}
                  className="w-full px-3 py-2 bg-sand-50 border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Folder Template</label>
                <input
                  type="text"
                  value={config.storage?.folder_template || ''}
                  onChange={e => setConfig({...config, storage: {...config.storage, folder_template: e.target.value}})}
                  className="w-full px-3 py-2 bg-sand-50 border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
                <p className="text-[11px] text-sand-400 mt-1">
                  Available: {'{email}'}, {'{date}'}, {'{sender}'}, {'{subject}'}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={config.storage?.verify_hash ?? true}
                  onChange={e => setConfig({...config, storage: {...config.storage, verify_hash: e.target.checked}})}
                  className="rounded border-sand-300 text-sunset-500 focus:ring-sunset-400"
                />
                <label className="text-sm text-warm-700">Verify file integrity with SHA-256 hash</label>
              </div>
            </div>
            <button onClick={handleSaveConfig}
              className="flex items-center gap-2 px-4 py-2 bg-sunset-500 text-white rounded-xl text-sm font-medium hover:bg-sunset-600 transition-colors">
              <Save className="w-4 h-4" /> Save Configuration
            </button>
          </div>
        )}

        {/* === Cloud Storage Tab === */}
        {tab === 'cloud' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-warm-900 flex items-center gap-2">
                <Cloud className="w-5 h-5 text-sunset-500" /> Cloud Storage
              </h3>
              <p className="text-sm text-sand-500 mt-1">
                Securely sync your documents to OneDrive or Google Drive
              </p>
            </div>

            {/* Connect Buttons */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={() => handleConnectCloud('onedrive')}
                className="flex items-center gap-3 px-5 py-4 bg-[#0078d4]/5 border-2 border-[#0078d4]/20
                           rounded-xl hover:bg-[#0078d4]/10 hover:border-[#0078d4]/40 transition-all group"
              >
                <div className="w-10 h-10 rounded-lg bg-[#0078d4] flex items-center justify-center shrink-0">
                  <Cloud className="w-5 h-5 text-white" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-semibold text-warm-900 group-hover:text-[#0078d4]">Connect with Microsoft</p>
                  <p className="text-[11px] text-sand-500">OneDrive</p>
                </div>
                <ExternalLink className="w-4 h-4 text-sand-400 ml-auto" />
              </button>

              <button
                onClick={() => handleConnectCloud('google_drive')}
                className="flex items-center gap-3 px-5 py-4 bg-[#4285f4]/5 border-2 border-[#4285f4]/20
                           rounded-xl hover:bg-[#4285f4]/10 hover:border-[#4285f4]/40 transition-all group"
              >
                <div className="w-10 h-10 rounded-lg bg-[#4285f4] flex items-center justify-center shrink-0">
                  <Cloud className="w-5 h-5 text-white" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-semibold text-warm-900 group-hover:text-[#4285f4]">Connect with Google</p>
                  <p className="text-[11px] text-sand-500">Google Drive</p>
                </div>
                <ExternalLink className="w-4 h-4 text-sand-400 ml-auto" />
              </button>
            </div>

            {/* Active Connections */}
            {cloudConnections.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-warm-800">Active Connections</h4>
                {cloudConnections.map((conn: any) => (
                  <div key={conn.id} className="flex items-center justify-between px-4 py-3 bg-sand-50 rounded-xl border border-sand-200">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                        conn.provider === 'onedrive' ? 'bg-[#0078d4]' : 'bg-[#4285f4]'
                      }`}>
                        <Cloud className="w-4 h-4 text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-warm-900">{conn.display_name}</p>
                        <p className="text-[11px] text-sand-500">
                          {conn.connected ? 'Connected' : 'Pending'}
                          {conn.total_synced > 0 && ` \u00B7 ${conn.total_synced} files synced`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                        conn.connected ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {conn.connected ? 'Active' : 'Pending'}
                      </span>
                      <button
                        onClick={() => handleDeleteCloud(conn.id)}
                        className="p-1.5 rounded-lg hover:bg-red-100 text-sand-400 hover:text-red-500 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Email OAuth Connect Buttons */}
            <div className="pt-4 border-t border-sand-200">
              <h4 className="text-sm font-medium text-warm-800 mb-3 flex items-center gap-2">
                <Link2 className="w-4 h-4 text-sunset-500" /> Connect Email via OAuth2
              </h4>
              <p className="text-xs text-sand-500 mb-3">Sign in securely with your email provider — no app passwords needed</p>
              <div className="flex gap-3">
                <button
                  onClick={() => handleConnectEmail('outlook')}
                  className="flex items-center gap-2 px-4 py-2.5 bg-[#0078d4]/10 border border-[#0078d4]/20
                             rounded-xl text-sm font-medium text-[#0078d4] hover:bg-[#0078d4]/20 transition-colors"
                >
                  <Mail className="w-4 h-4" /> Connect with Microsoft
                </button>
                <button
                  onClick={() => handleConnectEmail('gmail')}
                  className="flex items-center gap-2 px-4 py-2.5 bg-[#4285f4]/10 border border-[#4285f4]/20
                             rounded-xl text-sm font-medium text-[#4285f4] hover:bg-[#4285f4]/20 transition-colors"
                >
                  <Mail className="w-4 h-4" /> Connect with Google
                </button>
              </div>
            </div>
          </div>
        )}

        {/* === Email Rules Tab === */}
        {tab === 'rules' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-warm-900 flex items-center gap-2">
                  <ListFilter className="w-5 h-5 text-sunset-500" /> Email Rules
                </h3>
                <p className="text-sm text-sand-500 mt-0.5">Auto-label and classify incoming emails based on conditions</p>
              </div>
              <button onClick={() => setShowAddRule(!showAddRule)}
                className="flex items-center gap-1.5 px-3 py-2 bg-sunset-500 text-white rounded-xl text-xs font-medium hover:bg-sunset-600 transition-colors">
                <Plus className="w-3.5 h-3.5" /> Add Rule
              </button>
            </div>

            {/* Add Rule Form */}
            {showAddRule && (
              <div className="bg-sand-50 rounded-xl p-4 border border-sand-200 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-sand-600 mb-1 block">Rule Name</label>
                    <input type="text" placeholder="e.g. Amazon Receipts"
                      value={newRule.name} onChange={e => setNewRule({...newRule, name: e.target.value})}
                      className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-sand-600 mb-1 block">Priority (0-10)</label>
                    <input type="number" min={0} max={10}
                      value={newRule.priority} onChange={e => setNewRule({...newRule, priority: parseInt(e.target.value) || 0})}
                      className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                  </div>
                </div>

                {/* Conditions */}
                <div>
                  <label className="text-xs font-medium text-sand-600 mb-1.5 block">Conditions (all must match)</label>
                  {newRule.conditions.map((cond, i) => (
                    <div key={i} className="flex gap-2 mb-2">
                      <select value={cond.field} onChange={e => {
                        const c = [...newRule.conditions]; c[i] = {...c[i], field: e.target.value};
                        setNewRule({...newRule, conditions: c});
                      }} className="px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40">
                        {ruleFields?.fields?.map((f: any) => <option key={f.id} value={f.id}>{f.label}</option>)}
                      </select>
                      <select value={cond.operator} onChange={e => {
                        const c = [...newRule.conditions]; c[i] = {...c[i], operator: e.target.value};
                        setNewRule({...newRule, conditions: c});
                      }} className="px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40">
                        {ruleFields?.operators?.map((o: string) => <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>)}
                      </select>
                      <input type="text" placeholder="Value" value={cond.value}
                        onChange={e => {
                          const c = [...newRule.conditions]; c[i] = {...c[i], value: e.target.value};
                          setNewRule({...newRule, conditions: c});
                        }}
                        className="flex-1 px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                      {newRule.conditions.length > 1 && (
                        <button onClick={() => setNewRule({...newRule, conditions: newRule.conditions.filter((_, j) => j !== i)})}
                          className="text-red-400 hover:text-red-600"><Trash2 className="w-3.5 h-3.5" /></button>
                      )}
                    </div>
                  ))}
                  <button onClick={() => setNewRule({...newRule, conditions: [...newRule.conditions, { field: 'subject', operator: 'contains', value: '' }]})}
                    className="text-xs text-sunset-600 hover:text-sunset-700 font-medium">+ Add condition</button>
                </div>

                {/* Actions */}
                <div>
                  <label className="text-xs font-medium text-sand-600 mb-1.5 block">Actions</label>
                  {newRule.actions.map((act, i) => (
                    <div key={i} className="flex gap-2 mb-2">
                      <select value={act.action} onChange={e => {
                        const a = [...newRule.actions]; a[i] = {...a[i], action: e.target.value};
                        setNewRule({...newRule, actions: a});
                      }} className="px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40">
                        {ruleFields?.action_types?.map((a: any) => <option key={a.id} value={a.id}>{a.label}</option>)}
                      </select>
                      <input type="text" placeholder="Value" value={act.value}
                        onChange={e => {
                          const a = [...newRule.actions]; a[i] = {...a[i], value: e.target.value};
                          setNewRule({...newRule, actions: a});
                        }}
                        className="flex-1 px-2 py-1.5 bg-white border border-sand-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-sunset-400/40" />
                      {newRule.actions.length > 1 && (
                        <button onClick={() => setNewRule({...newRule, actions: newRule.actions.filter((_, j) => j !== i)})}
                          className="text-red-400 hover:text-red-600"><Trash2 className="w-3.5 h-3.5" /></button>
                      )}
                    </div>
                  ))}
                  <button onClick={() => setNewRule({...newRule, actions: [...newRule.actions, { action: 'label', value: '' }]})}
                    className="text-xs text-sunset-600 hover:text-sunset-700 font-medium">+ Add action</button>
                </div>

                <div className="flex gap-2 pt-1">
                  <button onClick={handleCreateRule}
                    className="px-4 py-2 bg-sunset-500 text-white rounded-lg text-xs font-medium hover:bg-sunset-600 transition-colors">
                    Create Rule
                  </button>
                  <button onClick={() => setShowAddRule(false)}
                    className="px-4 py-2 bg-sand-100 text-sand-600 rounded-lg text-xs font-medium hover:bg-sand-200 transition-colors">
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Rules List */}
            {rules.length === 0 ? (
              <div className="text-center py-8 text-sand-400">
                <ListFilter className="w-10 h-10 mx-auto mb-2 text-sand-300" />
                <p className="text-sm">No email rules configured</p>
              </div>
            ) : (
              <div className="space-y-2">
                {rules.map((rule: any) => (
                  <div key={rule.id} className="bg-sand-50 rounded-xl border border-sand-200 overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-3">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <button onClick={() => handleToggleRule(rule)} title={rule.enabled ? 'Disable' : 'Enable'}>
                          {rule.enabled
                            ? <ToggleRight className="w-5 h-5 text-green-500" />
                            : <ToggleLeft className="w-5 h-5 text-sand-400" />}
                        </button>
                        <div className="min-w-0">
                          <p className={`text-sm font-medium truncate ${rule.enabled ? 'text-warm-900' : 'text-sand-400'}`}>
                            {rule.name || 'Unnamed Rule'}
                          </p>
                          <p className="text-[11px] text-sand-500">
                            {rule.conditions?.length || 0} condition{rule.conditions?.length !== 1 ? 's' : ''}
                            {' \u00B7 '}{rule.actions?.length || 0} action{rule.actions?.length !== 1 ? 's' : ''}
                            {rule.match_count > 0 && ` \u00B7 ${rule.match_count} matches`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="px-2 py-0.5 bg-sand-200 text-sand-600 rounded text-[10px] font-medium">
                          P{rule.priority}
                        </span>
                        <button onClick={() => setExpandedRule(expandedRule === rule.id ? null : rule.id)}
                          className="p-1 rounded hover:bg-sand-200 text-sand-400">
                          {expandedRule === rule.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                        <button onClick={() => handleDeleteRule(rule.id)}
                          className="p-1 rounded hover:bg-red-100 text-sand-400 hover:text-red-500">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    {expandedRule === rule.id && (
                      <div className="px-4 pb-3 border-t border-sand-200 pt-2 space-y-2">
                        <div>
                          <p className="text-[11px] font-medium text-sand-500 mb-1">Conditions:</p>
                          {rule.conditions?.map((c: any, i: number) => (
                            <p key={i} className="text-xs text-warm-700 pl-2">
                              <span className="font-medium">{c.field}</span> {c.operator.replace(/_/g, ' ')} <span className="text-sunset-600">"{c.value}"</span>
                            </p>
                          ))}
                        </div>
                        <div>
                          <p className="text-[11px] font-medium text-sand-500 mb-1">Actions:</p>
                          {rule.actions?.map((a: any, i: number) => (
                            <p key={i} className="text-xs text-warm-700 pl-2">
                              <span className="font-medium">{a.action}</span> → <span className="text-sunset-600">"{a.value}"</span>
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* === Cloud Mode Tab === */}
        {tab === 'cloudmode' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-warm-900 flex items-center gap-2">
                <Globe className="w-5 h-5 text-sunset-500" /> Personal Cloud Mode
              </h3>
              <p className="text-sm text-sand-500 mt-1">
                Access Regia securely from anywhere using Tailscale or WireGuard
              </p>
            </div>

            {cloudModeInfo ? (
              <div className="space-y-4">
                {/* LAN Access */}
                <div className="bg-sand-50 rounded-xl border border-sand-200 p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center">
                      <Wifi className="w-4 h-4 text-green-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-warm-900">Local Network (LAN)</p>
                      <p className="text-[11px] text-sand-500">Available on your local network</p>
                    </div>
                    <span className="ml-auto px-2 py-0.5 rounded-full text-[10px] font-medium bg-green-100 text-green-700">Active</span>
                  </div>
                  <div className="mt-2 px-3 py-2 bg-white rounded-lg border border-sand-200 text-sm font-mono text-warm-800">
                    {cloudModeInfo.lan?.url}
                  </div>
                </div>

                {/* Tailscale */}
                <div className="bg-sand-50 rounded-xl border border-sand-200 p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      cloudModeInfo.tailscale ? 'bg-blue-100' : 'bg-sand-200'
                    }`}>
                      <Globe className={`w-4 h-4 ${cloudModeInfo.tailscale ? 'text-blue-600' : 'text-sand-400'}`} />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-warm-900">Tailscale</p>
                      <p className="text-[11px] text-sand-500">
                        {cloudModeInfo.tailscale ? `Connected · ${cloudModeInfo.tailscale.hostname}` : 'Not detected — install Tailscale for secure remote access'}
                      </p>
                    </div>
                    <span className={`ml-auto px-2 py-0.5 rounded-full text-[10px] font-medium ${
                      cloudModeInfo.tailscale ? 'bg-blue-100 text-blue-700' : 'bg-sand-200 text-sand-500'
                    }`}>
                      {cloudModeInfo.tailscale ? 'Connected' : 'Not installed'}
                    </span>
                  </div>
                  {cloudModeInfo.tailscale && (
                    <>
                      <div className="mt-2 px-3 py-2 bg-white rounded-lg border border-sand-200 text-sm font-mono text-warm-800">
                        {cloudModeInfo.tailscale.url}
                      </div>
                      {cloudModeInfo.tailscale.dns_name && (
                        <p className="text-[11px] text-sand-500 mt-1.5">
                          DNS: <span className="font-mono">{cloudModeInfo.tailscale.dns_name}</span>
                          {cloudModeInfo.tailscale.tailnet && ` · Tailnet: ${cloudModeInfo.tailscale.tailnet}`}
                        </p>
                      )}
                      {cloudModeInfo.tailscale.peers?.length > 0 && (
                        <div className="mt-3">
                          <p className="text-[11px] font-medium text-sand-500 mb-1">Peers ({cloudModeInfo.tailscale.peers.length}):</p>
                          <div className="space-y-1">
                            {cloudModeInfo.tailscale.peers.map((p: any, i: number) => (
                              <div key={i} className="flex items-center gap-2 text-xs text-warm-700">
                                <span className={`w-1.5 h-1.5 rounded-full ${p.online ? 'bg-green-500' : 'bg-sand-400'}`} />
                                <span className="font-medium">{p.hostname}</span>
                                <span className="text-sand-400 font-mono">{p.ip}</span>
                                <span className="text-sand-400">{p.os}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                  {!cloudModeInfo.tailscale && (
                    <div className="mt-2">
                      <a href="https://tailscale.com/download" target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs text-sunset-600 hover:text-sunset-700 font-medium">
                        <ExternalLink className="w-3.5 h-3.5" /> Install Tailscale
                      </a>
                    </div>
                  )}
                </div>

                {/* WireGuard */}
                <div className="bg-sand-50 rounded-xl border border-sand-200 p-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      cloudModeInfo.wireguard?.active ? 'bg-purple-100' : 'bg-sand-200'
                    }`}>
                      <Shield className={`w-4 h-4 ${cloudModeInfo.wireguard?.active ? 'text-purple-600' : 'text-sand-400'}`} />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-warm-900">WireGuard</p>
                      <p className="text-[11px] text-sand-500">
                        {cloudModeInfo.wireguard?.active
                          ? `Active · ${cloudModeInfo.wireguard.interfaces?.length || 0} interface(s)`
                          : 'Not detected — install WireGuard for manual VPN tunnels'}
                      </p>
                    </div>
                    <span className={`ml-auto px-2 py-0.5 rounded-full text-[10px] font-medium ${
                      cloudModeInfo.wireguard?.active ? 'bg-purple-100 text-purple-700' : 'bg-sand-200 text-sand-500'
                    }`}>
                      {cloudModeInfo.wireguard?.active ? 'Active' : 'Not active'}
                    </span>
                  </div>
                </div>

                {/* Recommended URL */}
                <div className="bg-sunset-50 rounded-xl border border-sunset-200 p-4">
                  <p className="text-xs font-medium text-sunset-700 mb-1.5">Recommended Access URL</p>
                  <div className="px-3 py-2 bg-white rounded-lg border border-sunset-200 text-sm font-mono text-warm-900 font-semibold">
                    {cloudModeInfo.recommended_url}
                  </div>
                  <p className="text-[11px] text-sunset-500 mt-1.5">
                    Use this URL from mobile or remote devices to connect to Regia
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-sand-400">
                <Globe className="w-10 h-10 mx-auto mb-2 text-sand-300" />
                <p className="text-sm">Loading cloud mode status...</p>
              </div>
            )}
          </div>
        )}

        {/* === Scheduler Tab === */}
        {tab === 'scheduler' && config && (
          <div className="space-y-4 max-w-lg">
            <h3 className="text-lg font-semibold text-warm-900 flex items-center gap-2">
              <Clock className="w-5 h-5 text-sunset-500" /> Scheduler Configuration
            </h3>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={config.scheduler?.enabled ?? true}
                  onChange={e => setConfig({...config, scheduler: {...config.scheduler, enabled: e.target.checked}})}
                  className="rounded border-sand-300 text-sunset-500 focus:ring-sunset-400"
                />
                <label className="text-sm text-warm-700">Enable automatic email polling</label>
              </div>
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Default Interval (minutes)</label>
                <input
                  type="number" min={1} max={1440}
                  value={config.scheduler?.default_interval_minutes || 15}
                  onChange={e => setConfig({...config, scheduler: {...config.scheduler, default_interval_minutes: parseInt(e.target.value) || 15}})}
                  className="w-full px-3 py-2 bg-sand-50 border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={config.scheduler?.retry_on_failure ?? true}
                  onChange={e => setConfig({...config, scheduler: {...config.scheduler, retry_on_failure: e.target.checked}})}
                  className="rounded border-sand-300 text-sunset-500 focus:ring-sunset-400"
                />
                <label className="text-sm text-warm-700">Retry on failure</label>
              </div>
            </div>
            <button onClick={handleSaveConfig}
              className="flex items-center gap-2 px-4 py-2 bg-sunset-500 text-white rounded-xl text-sm font-medium hover:bg-sunset-600 transition-colors">
              <Save className="w-4 h-4" /> Save Configuration
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
