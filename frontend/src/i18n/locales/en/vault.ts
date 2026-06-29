export default {
  // ── First-time Setup ────────────────────────────────────────
  setup: {
    title: 'Initialize Database Encryption',
    subtitle: 'Set an admin password and generate a recovery code for first deployment',
    username: 'Admin Username',
    usernamePlaceholder: 'Default: admin',
    password: 'Set Admin Password',
    passwordPlaceholder: '≥12 chars, upper/lower + digit + symbol',
    passwordHint: 'Leave blank to auto-generate',
    submit: 'Initialize & Generate Recovery Code',
    submitting: 'Initializing…',
  },

  // ── Recovery Code Display ───────────────────────────────────
  recovery: {
    title: 'Recovery Code Generated',
    warning: 'The recovery code is shown only once. It is the last resort if all passwords are lost. Save it offline immediately!',
    code: 'Recovery Code',
    adminPassword: 'Admin Password (auto-generated)',
    username: 'Username',
    copied: 'Copied to clipboard',
    enter: 'Enter System',
  },

  // ── Unlock ──────────────────────────────────────────────────
  unlock: {
    title: 'Database Locked',
    subtitle: 'Enter admin password or recovery code to unlock',
    tabPassword: 'Password',
    tabRecovery: 'Recovery Code',
    username: 'Username',
    usernamePlaceholder: 'Admin username',
    password: 'Password',
    passwordPlaceholder: 'Enter admin password',
    recoveryCode: 'Recovery Code',
    recoveryCodePlaceholder: 'Enter recovery code',
    submit: 'Unlock',
    submitting: 'Unlocking…',
    success: 'Unlocked successfully',
  },

  // ── Status ──────────────────────────────────────────────────
  status: {
    locked: 'Locked',
    unlocked: 'Unlocked',
    needsSetup: 'Needs Setup',
  },

  // ── Validation ──────────────────────────────────────────────
  validation: {
    usernameRequired: 'Username is required',
    passwordRequired: 'Password is required',
    recoveryRequired: 'Recovery code is required',
    passwordPolicy: '≥12 chars, upper/lower + digit + symbol',
  },

  // ── Common ──────────────────────────────────────────────────
  brand: 'Z-CMDB Encryption',
}
