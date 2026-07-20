import nextVitals from 'eslint-config-next/core-web-vitals';

const config = [
  ...nextVitals,
  {
    rules: {
      // Existing settings code intentionally hydrates client-only localStorage
      // state after mount.
      'react-hooks/set-state-in-effect': 'off',
    },
  },
];

export default config;
