// Optional Tailwind 3 mapping; Traccia itself keeps plain CSS.
module.exports = {
  "content": [
    "./replica/design/*.{html,js}"
  ],
  "theme": {
    "extend": {
      "colors": {
        "bg": "var(--tr-color-bg)",
        "surface": "var(--tr-color-surface)",
        "surface-subtle": "var(--tr-color-surface-subtle)",
        "border": "var(--tr-color-border)",
        "border-input": "var(--tr-color-border-input)",
        "text": "var(--tr-color-text)",
        "text-muted": "var(--tr-color-text-muted)",
        "accent": "var(--tr-color-accent)",
        "accent-hover": "var(--tr-color-accent-hover)",
        "accent-soft": "var(--tr-color-accent-soft)",
        "on-accent": "var(--tr-color-on-accent)",
        "focus": "var(--tr-color-focus)",
        "danger": "var(--tr-color-danger)",
        "danger-soft": "var(--tr-color-danger-soft)",
        "success": "var(--tr-color-success)",
        "success-soft": "var(--tr-color-success-soft)",
        "warning": "var(--tr-color-warning)",
        "warning-soft": "var(--tr-color-warning-soft)",
        "disabled-bg": "var(--tr-color-disabled-bg)",
        "disabled-text": "var(--tr-color-disabled-text)",
        "muted": "var(--tr-color-text-muted)"
      },
      "fontFamily": {
        "sans": [
          "var(--tr-font-sans)"
        ],
        "mono": [
          "var(--tr-font-mono)"
        ]
      },
      "spacing": {
        "0": "var(--tr-space-0)",
        "4": "var(--tr-space-4)",
        "8": "var(--tr-space-8)",
        "12": "var(--tr-space-12)",
        "16": "var(--tr-space-16)",
        "20": "var(--tr-space-20)",
        "24": "var(--tr-space-24)",
        "32": "var(--tr-space-32)",
        "40": "var(--tr-space-40)",
        "48": "var(--tr-space-48)",
        "64": "var(--tr-space-64)"
      },
      "borderRadius": {
        "sm": "var(--tr-radius-sm)",
        "md": "var(--tr-radius-md)",
        "lg": "var(--tr-radius-lg)",
        "pill": "var(--tr-radius-pill)"
      },
      "boxShadow": {
        "card": "var(--tr-shadow-card)",
        "pop": "var(--tr-shadow-pop)"
      },
      "fontSize": {
        "xs": [
          "var(--tr-type-xs-size)",
          {
            "lineHeight": "var(--tr-type-xs-line)",
            "fontWeight": "500"
          }
        ],
        "sm": [
          "var(--tr-type-sm-size)",
          {
            "lineHeight": "var(--tr-type-sm-line)",
            "fontWeight": "400"
          }
        ],
        "base": [
          "var(--tr-type-base-size)",
          {
            "lineHeight": "var(--tr-type-base-line)",
            "fontWeight": "400"
          }
        ],
        "lg": [
          "var(--tr-type-lg-size)",
          {
            "lineHeight": "var(--tr-type-lg-line)",
            "fontWeight": "600"
          }
        ],
        "xl": [
          "var(--tr-type-xl-size)",
          {
            "lineHeight": "var(--tr-type-xl-line)",
            "fontWeight": "600"
          }
        ],
        "display": [
          "var(--tr-type-display-size)",
          {
            "lineHeight": "var(--tr-type-display-line)",
            "fontWeight": "600"
          }
        ]
      }
    }
  }
};
