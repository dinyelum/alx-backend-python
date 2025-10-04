# Add to your existing serializers.py
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'first_name', 'last_name',
                  'email', 'phone_number', 'role', 'created_at']
        read_only_fields = ['user_id', 'created_at']
        extra_kwargs = {
            'password_hash': {'write_only': True}
        }
