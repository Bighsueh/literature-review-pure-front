// constants/uiConfig.ts
export const UI_CONFIG = {
  panels: {
    defaultLeftPanelWidth: 300,
    defaultRightPanelWidth: 300,
    minWidth: 200,
    maxWidth: 500
  },
  colors: {
    stages: {
      uploading: "blue",
      analyzing: "purple",
      saving: "green",
      extracting: "orange",
      searching: "teal",
      generating: "indigo",
      completed: "green",
      error: "red",
      idle: "gray"
    },
    types: {
      OD: "bg-blue-100 text-blue-800",
      CD: "bg-purple-100 text-purple-800",
      OTHER: "bg-gray-100 text-gray-800"
    }
  },
  animations: {
    progressBarTransition: "width 0.5s ease-in-out"
  }
};
