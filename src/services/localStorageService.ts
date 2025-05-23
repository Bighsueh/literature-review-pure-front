// services/localStorageService.ts
import { openDB, IDBPDatabase } from 'idb';
import { ProcessedSentence, FileMetadata } from '../types/file';
import { Message } from '../types/chat';

interface LocalStorageDB {
  sentences: ProcessedSentence[];
  fileMetadata: FileMetadata[];
  conversations: {
    id: string;
    messages: Message[];
  }[];
}

class LocalStorageService {
  private dbPromise: Promise<IDBPDatabase<LocalStorageDB>>;
  
  constructor() {
    this.dbPromise = openDB<LocalStorageDB>('pure-front-storage', 1, {
      upgrade(db) {
        // Create object stores if they don't exist
        if (!db.objectStoreNames.contains('sentences')) {
          db.createObjectStore('sentences', { keyPath: 'id' });
        }
        
        if (!db.objectStoreNames.contains('fileMetadata')) {
          db.createObjectStore('fileMetadata', { keyPath: 'id' });
        }
        
        if (!db.objectStoreNames.contains('conversations')) {
          db.createObjectStore('conversations', { keyPath: 'id' });
        }
      }
    });
  }
  
  // Sentences Storage
  async saveSentences(sentences: ProcessedSentence[]): Promise<void> {
    const db = await this.dbPromise;
    const tx = db.transaction('sentences', 'readwrite');
    const store = tx.objectStore('sentences');
    
    for (const sentence of sentences) {
      await store.put(sentence);
    }
    
    await tx.done;
  }
  
  async getSentencesByFileId(fileId: string): Promise<ProcessedSentence[]> {
    const db = await this.dbPromise;
    const tx = db.transaction('sentences', 'readonly');
    const store = tx.objectStore('sentences');
    const allSentences = await store.getAll();
    
    return allSentences.filter(sentence => sentence.fileId === fileId);
  }
  
  async getAllSentences(): Promise<ProcessedSentence[]> {
    const db = await this.dbPromise;
    const tx = db.transaction('sentences', 'readonly');
    const store = tx.objectStore('sentences');
    
    return store.getAll();
  }
  
  // File Metadata Storage
  async saveFileMetadata(metadata: FileMetadata): Promise<void> {
    const db = await this.dbPromise;
    const tx = db.transaction('fileMetadata', 'readwrite');
    const store = tx.objectStore('fileMetadata');
    
    await store.put(metadata);
    await tx.done;
  }
  
  async getFileMetadata(fileId: string): Promise<FileMetadata | undefined> {
    const db = await this.dbPromise;
    const tx = db.transaction('fileMetadata', 'readonly');
    const store = tx.objectStore('fileMetadata');
    
    return store.get(fileId);
  }
  
  async getAllFileMetadata(): Promise<FileMetadata[]> {
    const db = await this.dbPromise;
    const tx = db.transaction('fileMetadata', 'readonly');
    const store = tx.objectStore('fileMetadata');
    
    return store.getAll();
  }
  
  // Conversation Storage
  async saveConversation(conversationId: string, messages: Message[]): Promise<void> {
    const db = await this.dbPromise;
    const tx = db.transaction('conversations', 'readwrite');
    const store = tx.objectStore('conversations');
    
    await store.put({ id: conversationId, messages });
    await tx.done;
  }
  
  async getConversation(conversationId: string): Promise<Message[] | undefined> {
    const db = await this.dbPromise;
    const tx = db.transaction('conversations', 'readonly');
    const store = tx.objectStore('conversations');
    
    const conversation = await store.get(conversationId);
    return conversation?.messages;
  }
  
  async getAllConversations(): Promise<{ id: string; messages: Message[] }[]> {
    const db = await this.dbPromise;
    const tx = db.transaction('conversations', 'readonly');
    const store = tx.objectStore('conversations');
    
    return store.getAll();
  }
  
  // Cleanup
  async clearAll(): Promise<void> {
    const db = await this.dbPromise;
    const tx1 = db.transaction('sentences', 'readwrite');
    const tx2 = db.transaction('fileMetadata', 'readwrite');
    const tx3 = db.transaction('conversations', 'readwrite');
    
    await tx1.objectStore('sentences').clear();
    await tx2.objectStore('fileMetadata').clear();
    await tx3.objectStore('conversations').clear();
    
    await tx1.done;
    await tx2.done;
    await tx3.done;
  }
}

export const localStorageService = new LocalStorageService();
