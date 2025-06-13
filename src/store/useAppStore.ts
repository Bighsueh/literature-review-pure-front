import { defineStore } from 'pinia';
import { apiService, Paper, UploadResponse, PaperInfo } from '@/services/api_service';
import { paperMonitorService } from '@/services/paper_monitor_service';

interface ActiveTask {
  paperId: string;
  filename: string;
  progress: number;
  step: string;
}

export const useAppStore = defineStore('app', {
  state: () => ({
    papers: [] as PaperInfo[],
    selectedPapers: new Set<string>(),
    activeTasks: [] as ActiveTask[],
    isLoading: false,
    isUploading: false,
    uploadProgress: 0,
    error: null as string | null,
    currentPaperForAnalysis: null as Paper | null,
  }),

  getters: {
    //
  },

  actions: {
    async fetchPapers() {
        this.isLoading = true;
        this.error = null;
        try {
            const response = await apiService.getPapers();
            if (response.success && response.data) {
                this.papers = response.data;
            } else {
                this.error = response.error || 'Failed to fetch papers.';
            }
        } catch (e) {
            this.error = e instanceof Error ? e.message : String(e);
        } finally {
            this.isLoading = false;
        }
    },

    async uploadPdf(file: File) {
      this.isLoading = true; // Use a general loading state
      this.error = null;
      try {
        // Note: The base api_service doesn't support progress events with fetch,
        // so we can't show granular upload progress, only "uploading..."
        const response = await apiService.uploadFile(file);

        if (response.success && response.data) {
          const { paper_id, original_filename } = response.data;
          // Use a default name if original_filename is not provided
          const filename = original_filename || file.name;
          
          if (paper_id) {
            this.startPaperMonitoring(paper_id, filename);
          }
          await this.fetchPapers(); // Refresh the list
        } else {
          this.error = response.error || 'File upload failed.';
        }
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e);
      } finally {
        this.isLoading = false;
      }
    },

    startPaperMonitoring(paperId: string, filename: string) {
      if (this.activeTasks.some(t => t.paperId === paperId)) return;

      this.activeTasks.push({
        paperId,
        filename,
        progress: 0,
        step: '排隊中',
      });

      paperMonitorService.startMonitoring(paperId, {
        onProgress: (status) => {
          const taskIndex = this.activeTasks.findIndex(t => t.paperId === paperId);
          if (taskIndex !== -1) {
            this.activeTasks[taskIndex].progress = status.progress?.percentage ?? this.activeTasks[taskIndex].progress;
            this.activeTasks[taskIndex].step = status.progress?.step_name ?? '處理中...';
          }
        },
        onComplete: () => {
          this.activeTasks = this.activeTasks.filter(t => t.paperId !== paperId);
          this.fetchPapers();
        },
        onError: (errorMessage) => {
          const taskIndex = this.activeTasks.findIndex(t => t.paperId === paperId);
          if (taskIndex !== -1) {
            this.activeTasks[taskIndex].step = `錯誤`;
            this.activeTasks[taskIndex].progress = 100;
          }
          setTimeout(() => {
            this.activeTasks = this.activeTasks.filter(t => t.paperId !== paperId);
            this.fetchPapers();
          }, 5000);
        }
      });
    },

    clearError() {
      this.error = null;
    },
  },
}); 