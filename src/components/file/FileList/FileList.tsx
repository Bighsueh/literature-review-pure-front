import React, { useEffect } from 'react';
import { useAppStore } from '../../../stores/app_store';
import PaperSelectionPanel from '../PaperSelectionPanel/PaperSelectionPanel';

interface FileListProps {
  onFileSelect?: (paperId: string) => void;
}

const FileList: React.FC<FileListProps> = ({ onFileSelect }) => {
  const { refreshPapers } = useAppStore();

  // 初始化時載入論文列表
  useEffect(() => {
    refreshPapers();
  }, [refreshPapers]);



  return (
    <div className="h-full">
      <PaperSelectionPanel />
    </div>
  );
};

export default FileList;
