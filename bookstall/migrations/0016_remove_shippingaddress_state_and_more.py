# Generated by Django 5.2 on 2025-06-10 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookstall', '0015_alter_shippingaddress_state'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='shippingaddress',
            name='state',
        ),
        migrations.AddField(
            model_name='shippingaddress',
            name='district',
            field=models.CharField(blank=True, choices=[('Thiruvananthapuram', 'Thiruvananthapuram'), ('Kollam', 'Kollam'), ('Pathanamthitta', 'Pathanamthitta'), ('Alappuzha', 'Alappuzha'), ('Kottayam', 'Kottayam'), ('Idukki', 'Idukki'), ('Ernakulam', 'Ernakulam'), ('Thrissur', 'Thrissur'), ('Palakkad', 'Palakkad'), ('Malappuram', 'Malappuram'), ('Kozhikode', 'Kozhikode'), ('Wayanad', 'Wayanad'), ('Kannur', 'Kannur'), ('Kasaragod', 'Kasaragod')], max_length=100, null=True),
        ),
    ]
