export default {
  title: 'nmap Scan Command Reference',
  subtitle: 'Command templates can be copied directly · Output format must be XML (-oX), the system only parses XML',
  commands: {
    standard: {
      title: 'Standard Scan',
      badge: 'Recommended',
      desc: 'Covers ports 1-10000, suitable for daily asset inventory, takes ~10-30 minutes (/24 subnet)',
    },
    quick: {
      title: 'Quick Scan',
      badge: 'Fast',
      desc: 'Scans only Top 1000 ports, suitable for quick host alive check, takes ~3-10 minutes',
    },
    deep: {
      title: 'Deep Scan',
      badge: 'Slow but thorough',
      desc: 'Scans all 65535 ports, suitable for security audit / HVV full inventory, takes 30 min - hours',
    },
  },
  copy: 'Copy',
  copySuccess: 'Command copied to clipboard',
  copyFailed: 'Copy failed, please select and copy manually',
  notices: {
    title: 'Important Notes',
    items: {
      privileges: '-sS (SYN scan) and -O (OS detection) require root / admin privileges',
      uploadLimit: 'Upload file size limit is <b>50 MB</b> (adjustable in System Config)',
      subnet: 'Recommended to split scans by /24 subnet to avoid oversized single files',
      windows: 'On Windows, $(date ...) is not available, please name files manually',
      filtered: 'If many ports show filtered, consider reducing scan speed (-T3 or -T2)',
    },
  },
}
