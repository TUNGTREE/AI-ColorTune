import { useState, useEffect, useCallback } from 'react';
import { Modal, List, Button, Typography, Input, Empty, Popconfirm, message, theme } from 'antd';
import { DeleteOutlined, EditOutlined, CheckOutlined, UserOutlined } from '@ant-design/icons';
import { getSavedProfiles, deleteProfile, renameProfile } from '../../utils/profileStorage';
import { useAppStore } from '../../stores/appStore';
import type { SavedProfile } from '../../utils/profileStorage';

const { Text } = Typography;

interface ProfileManagerProps {
  open: boolean;
  onClose: () => void;
}

export default function ProfileManager({ open, onClose }: ProfileManagerProps) {
  const { token } = theme.useToken();
  const { loadSavedProfile } = useAppStore();
  const [profiles, setProfiles] = useState<SavedProfile[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  const refresh = useCallback(() => {
    setProfiles(getSavedProfiles());
  }, []);

  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  const handleDelete = (profileId: string) => {
    deleteProfile(profileId);
    refresh();
    message.success('Profile deleted');
  };

  const handleStartEdit = (saved: SavedProfile) => {
    setEditingId(saved.profile.id);
    setEditName(saved.name);
  };

  const handleSaveEdit = (profileId: string) => {
    if (editName.trim()) {
      renameProfile(profileId, editName.trim());
      refresh();
    }
    setEditingId(null);
  };

  const handleLoad = (saved: SavedProfile) => {
    loadSavedProfile(saved.profile);
    onClose();
    message.success(`Loaded profile: ${saved.name}`);
  };

  return (
    <Modal
      title="Saved Style Profiles"
      open={open}
      onCancel={onClose}
      footer={null}
      width={520}
    >
      {profiles.length === 0 ? (
        <Empty
          description={
            <Text style={{ color: 'rgba(255,255,255,0.45)' }}>
              No saved profiles yet. Complete style discovery to create one.
            </Text>
          }
        />
      ) : (
        <List
          dataSource={profiles}
          renderItem={(saved) => {
            const isEditing = editingId === saved.profile.id;
            const date = new Date(saved.savedAt);
            const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            return (
              <List.Item
                style={{
                  borderBottom: '1px solid #2a2a2a',
                  padding: '12px 0',
                }}
                actions={[
                  <Button
                    key="load"
                    type="primary"
                    size="small"
                    onClick={() => handleLoad(saved)}
                  >
                    Use
                  </Button>,
                  isEditing ? (
                    <Button
                      key="save-edit"
                      type="text"
                      size="small"
                      icon={<CheckOutlined />}
                      onClick={() => handleSaveEdit(saved.profile.id)}
                    />
                  ) : (
                    <Button
                      key="edit"
                      type="text"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => handleStartEdit(saved)}
                      style={{ color: 'rgba(255,255,255,0.45)' }}
                    />
                  ),
                  <Popconfirm
                    key="delete"
                    title="Delete this profile?"
                    onConfirm={() => handleDelete(saved.profile.id)}
                    okText="Yes"
                    cancelText="No"
                  >
                    <Button
                      type="text"
                      size="small"
                      icon={<DeleteOutlined />}
                      danger
                    />
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 8,
                        background: `linear-gradient(135deg, ${token.colorPrimary}, #8b5cf6)`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <UserOutlined style={{ color: '#fff', fontSize: 16 }} />
                    </div>
                  }
                  title={
                    isEditing ? (
                      <Input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        onPressEnter={() => handleSaveEdit(saved.profile.id)}
                        size="small"
                        autoFocus
                        style={{ width: 200 }}
                      />
                    ) : (
                      <Text style={{ color: 'rgba(255,255,255,0.85)' }}>
                        {saved.name}
                      </Text>
                    )
                  }
                  description={
                    <Text style={{ color: 'rgba(255,255,255,0.35)', fontSize: 12 }}>
                      Created {dateStr}
                    </Text>
                  }
                />
              </List.Item>
            );
          }}
        />
      )}
    </Modal>
  );
}
