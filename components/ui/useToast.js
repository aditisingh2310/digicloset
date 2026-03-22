import { Toast } from '@shopify/app-bridge/actions';
import { useAppBridge } from '@shopify/app-bridge-react';

export default function useToast() {
  const app = useAppBridge();

  return (message) => {
    const toast = Toast.create(app, { message });
    toast.dispatch(Toast.Action.SHOW);
  };
}
